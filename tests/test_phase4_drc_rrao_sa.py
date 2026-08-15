from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import pytest

from frtb_lab.sa.curvature import curvature_capital
from frtb_lab.sa.drc import (
    ARTIFACTS as DRC_ARTIFACTS,
)
from frtb_lab.sa.drc import (
    DRCExposure,
    bucket_results,
    calculate_non_securitisation_drc,
    canonical_drc_exposures,
    drc_case_exposures,
    gross_jtd,
    hedge_benefit_ratio,
    lgd_for_seniority,
    maturity_scale,
    net_jtd_by_obligor,
    risk_weight_for_credit_quality,
    seniority_offset_permitted,
    validate_drc_scope,
)
from frtb_lab.sa.rrao import (
    ARTIFACT_PATH as RRAO_ARTIFACT,
)
from frtb_lab.sa.rrao import (
    EXOTIC_UNDERLYING,
    OTHER_RESIDUAL_RISK,
    RRAOInstrument,
    calculate_rrao,
    classify_and_calculate,
    rrao_case_instruments,
)
from frtb_lab.sa.sbm import calculate_selected_scope_sbm
from frtb_lab.sa.standardised import (
    ARTIFACT_PATH as SA_ARTIFACT,
)
from frtb_lab.sa.standardised import (
    calculate_selected_scope_standardised_approach,
)
from frtb_lab.sensitivities.common import load_yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = REPO_ROOT / "data" / "fixtures" / "canonical_portfolio.yaml"
RRAO_INVENTORY = REPO_ROOT / "governance" / "rrao_inventory.csv"
PARAMETER_CROSSWALK = REPO_ROOT / "regulatory" / "parameter_crosswalk.csv"


def _parameter_rows() -> dict[str, dict[str, str]]:
    with PARAMETER_CROSSWALK.open(newline="") as handle:
        return {row["parameter_id"]: row for row in csv.DictReader(handle)}


def _canonical_instrument(instrument_id: str) -> dict:
    portfolio = load_yaml(PORTFOLIO_PATH)
    return next(row for row in portfolio["instruments"] if row["instrument_id"] == instrument_id)


def test_phase3_total_decomposition_regression_and_tie_explanation() -> None:
    output = calculate_selected_scope_sbm(write_artifacts=False)
    totals = set()
    for row in output["scenario_results"]:
        component_sum = (
            row["gir_delta"]
            + row["equity_delta"]
            + row["fx_delta"]
            + row["equity_vega"]
            + row["fx_vega"]
            + row["equity_curvature"]
            + row["fx_curvature"]
        )
        assert row["selected_scope_sbm_total"] == pytest.approx(component_sum, abs=1e-9)
        totals.add(round(row["selected_scope_sbm_total"], 8))
    assert len(totals) == 1
    report = (REPO_ROOT / "reports" / "sections" / "sbm_aggregation_and_curvature.md").read_text()
    assert "one bucket per implemented" in report
    assert "Non-trivial correlation behavior is covered by deterministic test fixtures" in report


def test_positive_curvature_control_produces_capital() -> None:
    records = [
        {
            "risk_class": "EQUITY",
            "bucket": "EQUITY_BUCKET_12",
            "risk_factor_id": "RF_TEST_SHORT_OPTION",
            "cvr_up": 125.0,
            "cvr_down": 75.0,
        }
    ]
    result = curvature_capital(records, "MEDIUM")
    assert result["risk_class_capital"] == pytest.approx(125.0)
    assert result["bucket_results"][0]["selected_direction"] == "up"


def test_canonical_corporate_bond_drc_metadata_is_complete_and_separate_from_sbm() -> None:
    corp = _canonical_instrument("SYN_CORP_BOND")
    assert corp["primary_risk_class"] == "CSR_NON_SECURITISATION"
    assert corp["drc_relevant"] is True
    metadata = corp["drc_metadata"]
    assert metadata["obligor_id"] == "SYN_CORP_A"
    assert metadata["credit_quality_category"] == "BBB"
    assert metadata["seniority"] == "senior_debt"
    assert metadata["face_value"] == 600000
    assert metadata["market_value"] == 570000
    assert metadata["default_direction"] == "long"
    assert metadata["drc_bucket"] == "corporates"


def test_default_direction_uses_default_loss_economics_not_trade_label() -> None:
    misleading = DRCExposure(
        instrument_id="SOLD_PUT_ON_BOND_CONTROL",
        obligor_id="SYN_OBLIGOR_X",
        obligor_type="corporate",
        credit_quality_category="BBB",
        seniority="senior_debt",
        bond_equivalent_notional=100000.0,
        market_value=98000.0,
        cumulative_pnl=-2000.0,
        remaining_maturity_years=1.0,
        default_direction="long",
        drc_bucket="corporates",
    )
    assert gross_jtd(misleading).gross_jtd == pytest.approx(73000.0)


def test_gross_jtd_includes_lgd_notional_and_pnl_adjustment() -> None:
    exposure = canonical_drc_exposures()[0]
    result = gross_jtd(exposure)
    expected = 0.75 * 600000.0 - 30000.0
    assert result.gross_jtd == pytest.approx(expected)
    assert result.scaled_gross_jtd == pytest.approx(expected)


def test_lgd_values_match_selected_source_table() -> None:
    assert lgd_for_seniority("senior_debt") == pytest.approx(0.75)
    assert lgd_for_seniority("equity_or_non_senior_debt") == pytest.approx(1.0)
    assert lgd_for_seniority("covered_bond") == pytest.approx(0.25)


def test_maturity_scaling_and_three_month_floor() -> None:
    assert maturity_scale(2.0) == pytest.approx(1.0)
    assert maturity_scale(0.5) == pytest.approx(0.5)
    assert maturity_scale(1.0 / 12.0) == pytest.approx(0.25)
    exposure = DRCExposure(
        instrument_id="ONE_MONTH",
        obligor_id="SYN_OBLIGOR_M",
        obligor_type="corporate",
        credit_quality_category="BBB",
        seniority="senior_debt",
        bond_equivalent_notional=100000.0,
        market_value=100000.0,
        cumulative_pnl=0.0,
        remaining_maturity_years=1.0 / 12.0,
        default_direction="long",
        drc_bucket="corporates",
    )
    result = gross_jtd(exposure)
    assert result.gross_jtd == pytest.approx(75000.0)
    assert result.scaled_gross_jtd == pytest.approx(18750.0)


def test_same_obligor_netting_and_seniority_rules() -> None:
    net = {
        row.obligor_id: row
        for row in net_jtd_by_obligor([gross_jtd(x) for x in drc_case_exposures()])
    }
    assert seniority_offset_permitted("senior_debt", "equity_or_non_senior_debt") is True
    assert seniority_offset_permitted("equity_or_non_senior_debt", "senior_debt") is False
    assert net["SYN_OBLIGOR_A"].net_long_jtd == pytest.approx(550000.0)
    assert net["SYN_OBLIGOR_A"].net_short_jtd == pytest.approx(0.0)
    assert "PERMITTED_OFFSET=180000.0000000000" in net["SYN_OBLIGOR_A"].netting_status
    assert net["SYN_OBLIGOR_B"].net_long_jtd == pytest.approx(270000.0)
    assert net["SYN_OBLIGOR_B"].net_short_jtd == pytest.approx(-70000.0)
    assert "REJECTED_OFFSET=70000.0000000000" in net["SYN_OBLIGOR_B"].netting_status
    assert net["SYN_OBLIGOR_C"].net_long_jtd == pytest.approx(182500.0)


def test_different_obligors_are_not_netted_and_signs_are_preserved() -> None:
    net = net_jtd_by_obligor([gross_jtd(x) for x in drc_case_exposures()])
    assert len(net) == 4
    assert sum(row.net_long_jtd for row in net) == pytest.approx(1002500.0)
    assert sum(row.net_short_jtd for row in net) == pytest.approx(-175000.0)


def test_drc_bucket_scope_and_rating_weights() -> None:
    assert risk_weight_for_credit_quality("AAA") == pytest.approx(0.005)
    assert risk_weight_for_credit_quality("BBB") == pytest.approx(0.06)
    assert risk_weight_for_credit_quality("Defaulted") == pytest.approx(1.0)
    with pytest.raises(ValueError, match="Unsupported credit quality"):
        risk_weight_for_credit_quality("MADE_UP")
    bad_bucket = canonical_drc_exposures()[0]
    with pytest.raises(ValueError, match="Unsupported non-securitisation"):
        validate_drc_scope(
            DRCExposure(**{**bad_bucket.__dict__, "drc_bucket": "commodities"})
        )
    with pytest.raises(ValueError, match="Securitisation DRC"):
        validate_drc_scope(
            DRCExposure(**{**bad_bucket.__dict__, "securitisation_flag": True})
        )


def test_hbr_uses_unweighted_net_jtd_and_edge_cases() -> None:
    assert hedge_benefit_ratio(100.0, 0.0) == pytest.approx(1.0)
    assert hedge_benefit_ratio(0.0, -50.0) == pytest.approx(0.0)
    assert hedge_benefit_ratio(0.0, 0.0) == pytest.approx(0.0)
    assert hedge_benefit_ratio(1002500.0, -175000.0) == pytest.approx(
        1002500.0 / (1002500.0 + 175000.0)
    )


def test_bucket_drc_matches_independent_hand_calculation() -> None:
    net = net_jtd_by_obligor([gross_jtd(x) for x in drc_case_exposures()])
    bucket = bucket_results(net)[0]
    long_weighted = 550000.0 * 0.03 + 270000.0 * 0.15 + 182500.0 * 0.06
    short_weighted = 70000.0 * 0.15 + 105000.0 * 0.30
    hbr = 1002500.0 / (1002500.0 + 175000.0)
    expected = max(long_weighted - hbr * short_weighted, 0.0)
    assert bucket.weighted_long_jtd == pytest.approx(long_weighted)
    assert abs(bucket.weighted_short_jtd) == pytest.approx(short_weighted)
    assert bucket.hbr == pytest.approx(hbr)
    assert bucket.bucket_drc == pytest.approx(expected)
    case_result = calculate_non_securitisation_drc(
        drc_case_exposures(),
        write_artifacts=False,
    )
    assert case_result.total_drc == pytest.approx(expected)


def test_bucket_floor_and_no_cross_bucket_diversification() -> None:
    floored = bucket_results(
        [
            type(
                "Net",
                (),
                {
                    "drc_bucket": "corporates",
                    "net_long_jtd": 10.0,
                    "net_short_jtd": 0.0,
                    "credit_quality_category": "BBB",
                },
            )(),
            type(
                "Net",
                (),
                {
                    "drc_bucket": "corporates",
                    "net_long_jtd": 0.0,
                    "net_short_jtd": -100.0,
                    "credit_quality_category": "Defaulted",
                },
            )(),
        ]
    )[0]
    assert floored.bucket_drc == pytest.approx(0.0)
    multi = bucket_results(
        [
            type(
                "Net",
                (),
                {
                    "drc_bucket": "corporates",
                    "net_long_jtd": 100.0,
                    "net_short_jtd": 0.0,
                    "credit_quality_category": "BBB",
                },
            )(),
            type(
                "Net",
                (),
                {
                    "drc_bucket": "sovereigns",
                    "net_long_jtd": 200.0,
                    "net_short_jtd": 0.0,
                    "credit_quality_category": "A",
                },
            )(),
        ]
    )
    assert sum(bucket.bucket_drc for bucket in multi) == pytest.approx(100.0 * 0.06 + 200.0 * 0.03)


def test_canonical_drc_result() -> None:
    result = calculate_non_securitisation_drc(write_artifacts=True)
    assert result.gross_jtd[0].gross_jtd == pytest.approx(420000.0)
    assert result.net_jtd[0].net_long_jtd == pytest.approx(420000.0)
    assert result.buckets[0].hbr == pytest.approx(1.0)
    assert result.total_drc == pytest.approx(25200.0)


def test_barrier_rrao_classification_and_additive_scope() -> None:
    barrier = _canonical_instrument("SYN_EQ_BARRIER")
    assert barrier["primary_risk_class"] == "EQUITY"
    assert barrier["rrao_candidate"] is True
    with RRAO_INVENTORY.open(newline="") as handle:
        rows = {row["instrument_id"]: row for row in csv.DictReader(handle)}
    row = rows["SYN_EQ_BARRIER"]
    assert row["rrao_category"] == OTHER_RESIDUAL_RISK
    assert row["exotic_underlying"] == "false"
    result = classify_and_calculate(
        RRAOInstrument(
            instrument_id="SYN_EQ_BARRIER",
            underlying_type="ordinary_equity",
            path_dependent=True,
            multi_underlying=False,
            other_residual_risk=True,
            exotic_underlying=False,
            listed_or_ccp_eligible=False,
            back_to_back=False,
            gross_notional=250000.0,
        )
    )
    assert result.risk_weight == pytest.approx(0.001)
    assert result.rrao_contribution == pytest.approx(250.0)


def test_exotic_underlying_and_rrao_exclusions_are_category_specific() -> None:
    rows = {row.instrument_id: classify_and_calculate(row) for row in rrao_case_instruments()}
    exotic = rows["SYN_EXOTIC_UNDERLYING_NOTE"]
    assert exotic.rrao_category == EXOTIC_UNDERLYING
    assert exotic.risk_weight == pytest.approx(0.01)
    assert exotic.included is True
    assert exotic.rrao_contribution == pytest.approx(10000.0)
    listed_other = rows["SYN_LISTED_BARRIER_CONTROL"]
    assert listed_other.rrao_category == OTHER_RESIDUAL_RISK
    assert listed_other.included is False
    assert listed_other.exclusion_reason == "listed_or_ccp_other_residual_risk"
    back_to_back = rows["SYN_BACK_TO_BACK_BARRIER"]
    assert back_to_back.included is False
    assert back_to_back.exclusion_reason == "exact_back_to_back"


def test_rrao_uses_gross_notional_without_netting() -> None:
    instruments = [
        RRAOInstrument("A", "ordinary_equity", True, False, True, False, False, False, 100.0),
        RRAOInstrument("B", "ordinary_equity", True, False, True, False, False, False, 200.0),
    ]
    result = calculate_rrao(instruments, write_artifact=False)
    assert [row.rrao_contribution for row in result.rows] == [0.1, 0.2]
    assert result.total_rrao == pytest.approx(0.3)


def test_selected_standardised_approach_integration_uses_binding_sbm_once() -> None:
    result = calculate_selected_scope_standardised_approach(write_artifacts=True)
    assert result["selected_sbm"] == pytest.approx(601060.6801585773)
    assert result["non_securitisation_drc"] == pytest.approx(25200.0)
    assert result["rrao"] == pytest.approx(250.0)
    assert result["selected_scope_standardised_approach_capital"] == pytest.approx(
        result["selected_sbm"] + result["non_securitisation_drc"] + result["rrao"]
    )
    assert result["selected_scope_standardised_approach_capital"] < 3 * result["selected_sbm"]
    assert all("selected-scope" in row["scope_label"] for row in result["rows"])


def test_phase4_parameter_provenance_is_complete() -> None:
    rows = _parameter_rows()
    required = {
        "DRC_GROSS_JTD_FORMULA",
        "DRC_LGD_EQUITY_NONSENIOR",
        "DRC_LGD_SENIOR_DEBT",
        "DRC_LGD_COVERED_BOND",
        "DRC_MATURITY_CAPITAL_HORIZON",
        "DRC_MATURITY_FLOOR",
        "DRC_SENIORITY_OFFSET_RULE",
        "DRC_NONSEC_BUCKETS",
        "DRC_HBR_FORMULA",
        "DRC_BUCKET_FORMULA",
        "DRC_ACROSS_BUCKET_SUM",
        "DRC_RW_AAA",
        "DRC_RW_AA",
        "DRC_RW_A",
        "DRC_RW_BBB",
        "DRC_RW_BB",
        "DRC_RW_B",
        "DRC_RW_CCC",
        "DRC_RW_UNRATED",
        "DRC_RW_DEFAULTED",
        "RRAO_CATEGORY_EXOTIC_UNDERLYING",
        "RRAO_CATEGORY_OTHER_RESIDUAL_RISK",
        "RRAO_EXACT_BACK_TO_BACK_EXCLUSION",
        "RRAO_LISTED_CCP_OTHER_RESIDUAL_EXCLUSION",
        "RRAO_ADDITIVE_SCOPE_RULE",
        "RRAO_RW_EXOTIC_UNDERLYING",
        "RRAO_RW_OTHER_RESIDUAL_RISK",
        "RRAO_GROSS_NOTIONAL_SUM_FORMULA",
    }
    assert required <= set(rows)
    for parameter_id in required:
        row = rows[parameter_id]
        assert row["implementation_status"] == "IMPLEMENTED"
        assert row["source_id"] in {"BIS_MAR22", "BIS_MAR23"}
        assert row["source_paragraph_or_table"].startswith(("MAR22", "MAR23"))


def test_no_phase5_or_out_of_scope_engines_exist() -> None:
    forbidden = [
        REPO_ROOT / "src" / "frtb_lab" / "ima",
        REPO_ROOT / "src" / "frtb_lab" / "sa" / "securitisation_drc.py",
        REPO_ROOT / "src" / "frtb_lab" / "sa" / "ctp.py",
        REPO_ROOT / "src" / "frtb_lab" / "rfet.py",
        REPO_ROOT / "src" / "frtb_lab" / "pla.py",
        REPO_ROOT / "src" / "frtb_lab" / "backtesting.py",
        REPO_ROOT / "data" / "artifacts" / "ima_capital.csv",
        REPO_ROOT / "data" / "artifacts" / "rfet.csv",
        REPO_ROOT / "data" / "artifacts" / "pla.csv",
        REPO_ROOT / "data" / "artifacts" / "backtesting.csv",
    ]
    assert not any(path.exists() for path in forbidden)


def test_phase4_artifacts_and_private_files_are_ignored_and_untracked() -> None:
    calculate_selected_scope_standardised_approach(write_artifacts=True)
    phase4_paths = [
        *(str(path.relative_to(REPO_ROOT)) for path in DRC_ARTIFACTS.values()),
        str(RRAO_ARTIFACT.relative_to(REPO_ROOT)),
        str(SA_ARTIFACT.relative_to(REPO_ROOT)),
    ]
    private_paths = ["PROJECT_FRTB_V2_SPEC.md", "FRTB_V2_STATUS.md", "local_frtb_v2_baseline/"]
    ignored = subprocess.run(
        ["git", "check-ignore", *phase4_paths, *private_paths],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert ignored.returncode == 0
    tracked = subprocess.run(
        ["git", "ls-files", *phase4_paths, *private_paths],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert tracked.stdout == ""


def test_no_tracked_local_path_or_positive_overclaim() -> None:
    leaked_path = "/Users/" + "linruihe/"
    path_scan = subprocess.run(
        ["git", "grep", "-n", leaked_path, "--", "."],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert path_scan.returncode == 1
    prohibited = [
        "regulatory " + "compliant",
        "Basel " + "compliant",
        "FRTB " + "compliant",
        "approved " + "by",
        "portfolio regulatory " + "capital",
    ]
    for phrase in prohibited:
        scan = subprocess.run(
            ["git", "grep", "-n", "-i", phrase, "--", "."],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert scan.returncode == 1
