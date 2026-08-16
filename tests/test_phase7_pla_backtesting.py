from __future__ import annotations

import csv
import subprocess
from pathlib import Path
from typing import Any

import pytest
from repo_scan import format_matches, scan_public_text

from frtb_lab.ima.backtesting import (
    backtesting_sample,
    calculate_backtesting,
    calibration_rows_for_date,
    desk_backtest_threshold,
    historical_var,
    is_exception,
    threshold_status,
)
from frtb_lab.ima.desk_eligibility import (
    AMBER_SURCHARGE_DEFERRED,
    IMA_TEST_GATE_PASS,
    PLA_AMBER_DIAGNOSTIC,
    SA_FALLBACK_REQUIRED,
    calculate_phase7_desk_diagnostics,
    diagnostic_status_for,
)
from frtb_lab.ima.es import calculate_phase5_ima_es
from frtb_lab.ima.pla import (
    ks_statistic,
    pla_zone,
    ranks,
    spearman_correlation,
)
from frtb_lab.ima.pnl import (
    generate_daily_pnl,
    load_desk_model_config,
    pla_sample,
    pnl_by_desk,
)
from frtb_lab.ima.rfet import calculate_phase6_rfet, reduced_set_rfet_audit
from frtb_lab.sa.standardised import calculate_selected_scope_standardised_approach

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def phase7_output() -> dict[str, Any]:
    return calculate_phase7_desk_diagnostics(write_artifacts=True)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _parameter_rows() -> dict[str, dict[str, str]]:
    return {
        row["parameter_id"]: row
        for row in _read_csv(REPO_ROOT / "regulatory" / "parameter_crosswalk.csv")
    }


def test_phase5_and_phase6_regression_outputs_are_unchanged() -> None:
    sa = calculate_selected_scope_standardised_approach(write_artifacts=False)
    phase5 = calculate_phase5_ima_es(write_artifacts=False)
    phase6 = calculate_phase6_rfet(write_artifacts=False)
    calibration = phase5["stress_calibration"]
    assert sa["selected_scope_standardised_approach_capital"] == pytest.approx(
        626510.6801585772
    )
    assert calibration.es_f_c == pytest.approx(135310.97891484312)
    assert calibration.es_r_c == pytest.approx(136600.78255244752)
    assert calibration.es_r_s == pytest.approx(377307.3028054556)
    assert calibration.raw_scaling_ratio == pytest.approx(0.9905578605517198)
    assert calibration.floored_scaling_ratio == pytest.approx(1.0)
    audit = reduced_set_rfet_audit(phase6["results"])
    assert audit["audit_status"] == "REDUCED_SET_RFET_MECHANICS_FAIL"
    assert audit["failed_reduced_factor_ids"] == (
        "RF_EQUITY_SPX_VOL_1Y",
        "RF_FX_EURUSD_SPOT",
    )
    rfet_findings = _read_csv(REPO_ROOT / "governance" / "rfet_findings.csv")
    assert {row["status"] for row in rfet_findings} == {"OPEN"}


def test_desk_model_specifications_are_frozen_before_metrics() -> None:
    cfg = load_desk_model_config()
    assert cfg["metadata"]["source_id"] == "BIS_MAR32"
    assert cfg["metadata"]["frozen_before_metric_evaluation"] is True
    assert cfg["metadata"]["evaluation_date"] == "2026-08-14"
    assert "pla_zone" not in str(cfg["desk_models"]).lower()
    assert cfg["global_rules"]["hpl_static_positions"] is True
    assert cfg["global_rules"]["hpl_excludes_intraday_trading"] is True
    assert cfg["global_rules"]["missing_data_rule"] == "MISSING_PNL_OR_VAR_COUNTS_AS_OUTLIER"


def test_daily_pnl_generation_is_deterministic_and_uses_synthetic_apl() -> None:
    first = generate_daily_pnl()
    second = generate_daily_pnl()
    assert first == second
    assert len(first) == 5118 * 3
    assert {row["apl_label"] for row in first} == {"SYNTHETIC_APL"}
    assert {row["desk_id"] for row in first} == {"TD-RATES", "TD-EQUITY", "TD-FX"}
    for row in first[:100]:
        assert row["static_positions"] is True
        assert row["hpl_excludes_intraday_trading"] is True
        assert float(row["apl"]) == pytest.approx(
            float(row["hpl"]) + float(row["apl_intraday_component"])
        )


def test_no_live_market_or_network_source_is_used_for_phase7_modules() -> None:
    for token in ["requests", "yfinance", "fred", "urllib", "httpx", "date.today"]:
        scan = subprocess.run(
            [
                "git",
                "grep",
                "-n",
                token,
                "--",
                "src/frtb_lab/ima/pnl.py",
                "src/frtb_lab/ima/pla.py",
                "src/frtb_lab/ima/backtesting.py",
                "src/frtb_lab/ima/desk_eligibility.py",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert scan.returncode == 1


def test_hpl_sample_is_identical_for_pla_and_backtesting() -> None:
    pnl_rows = generate_daily_pnl()
    grouped = pnl_by_desk(pnl_rows)
    pla_samples = pla_sample(pnl_rows)
    for desk_id, desk_rows in grouped.items():
        bt_sample = backtesting_sample(desk_rows)
        assert [row["date"] for row in pla_samples[desk_id]] == [
            row["date"] for row in bt_sample
        ]
        assert [row["hpl"] for row in pla_samples[desk_id]] == [
            row["hpl"] for row in bt_sample
        ]
        assert len(bt_sample) == 250
        assert bt_sample[0]["date"] == "2025-09-01"
        assert bt_sample[-1]["date"] == "2026-08-14"


def test_rtpl_uses_only_declared_model_factors_and_can_include_nmrf_candidates() -> None:
    cfg = load_desk_model_config()
    for desk in cfg["desk_models"].values():
        if not desk["selected_phase7_scope"]:
            continue
        assert set(desk["rtpl_factor_weights"]) == set(desk["included_rtpl_risk_factors"])
        assert set(desk["included_rtpl_risk_factors"]) <= set(desk["hpl_pricing_factors"])
    assert "RF_EQUITY_SPX_VOL_1Y" in cfg["desk_models"]["TD-EQUITY"]["included_rtpl_risk_factors"]
    assert "RF_EQUITY_SPX_VOL_1Y" in cfg["desk_models"]["TD-EQUITY"]["nmrf_candidate_factors"]
    assert "RF_FX_EURUSD_VOL_1Y" not in cfg["desk_models"]["TD-FX"]["included_rtpl_risk_factors"]


def test_spearman_ranks_ks_and_zone_thresholds() -> None:
    assert ranks([2.0, 1.0, 1.0]) == [3.0, 1.5, 1.5]
    assert spearman_correlation([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)
    assert spearman_correlation([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) == pytest.approx(-1.0)
    assert ks_statistic([0.0, 1.0], [0.0, 2.0]) == pytest.approx(0.5)
    assert pla_zone(0.800001, 0.089999) == "GREEN"
    assert pla_zone(0.80, 0.08) == "AMBER"
    assert pla_zone(0.81, 0.09) == "AMBER"
    assert pla_zone(0.699999, 0.08) == "RED"
    assert pla_zone(0.70, 0.08) == "AMBER"
    assert pla_zone(0.81, 0.120001) == "RED"
    assert pla_zone(0.81, 0.12) == "AMBER"


def test_pla_fixtures_cover_green_amber_and_red_cases() -> None:
    base = [float(index) for index in range(250)]
    green = calculate_pla_for_fixture(base, base)
    amber = calculate_pla_for_fixture(base, [float(index + 25) for index in range(250)])
    red_spearman = calculate_pla_for_fixture(base, list(reversed(base)))
    red_ks = calculate_pla_for_fixture(base, [float(index + 1000) for index in range(250)])
    assert green == "GREEN"
    assert amber == "AMBER"
    assert red_spearman == "RED"
    assert red_ks == "RED"


def calculate_pla_for_fixture(hpl: list[float], rtpl: list[float]) -> str:
    return pla_zone(spearman_correlation(hpl, rtpl), ks_statistic(hpl, rtpl))


def test_canonical_pla_results_are_traceable_and_deterministic(
    phase7_output: dict[str, Any],
) -> None:
    results = {row.desk_id: row for row in phase7_output["pla_results"]}
    assert set(results) == {"TD-RATES", "TD-EQUITY", "TD-FX"}
    assert results["TD-RATES"].pla_zone == "GREEN"
    assert results["TD-RATES"].spearman == pytest.approx(1.0)
    assert results["TD-RATES"].ks_statistic == pytest.approx(0.0)
    assert results["TD-EQUITY"].pla_zone == "GREEN"
    assert results["TD-EQUITY"].spearman == pytest.approx(0.9991651706427302)
    assert results["TD-EQUITY"].ks_statistic == pytest.approx(0.02400000000000002)
    assert results["TD-FX"].pla_zone == "RED"
    assert results["TD-FX"].spearman == pytest.approx(-0.9972781644506312)
    assert results["TD-FX"].ks_statistic == pytest.approx(0.20800000000000002)
    assert {row.observations for row in results.values()} == {250}


def test_historical_var_exception_logic_and_thresholds() -> None:
    assert historical_var([-1.0, -2.0, -3.0, -4.0], 0.75) == pytest.approx(3.0)
    assert historical_var([10.0, 20.0, 30.0], 0.99) == pytest.approx(0.0)
    assert is_exception(-100.0, 100.0) is False
    assert is_exception(-100.01, 100.0) is True
    assert is_exception(None, 100.0) is True
    assert is_exception(-100.0, None) is True
    assert desk_backtest_threshold(0.99) == 12
    assert desk_backtest_threshold(0.975) == 30
    assert threshold_status(0.99, 11) == "PASS"
    assert threshold_status(0.99, 12) == "PASS"
    assert threshold_status(0.99, 13) == "BREACH"
    assert threshold_status(0.975, 28) == "PASS"
    assert threshold_status(0.975, 29) == "PASS"
    assert threshold_status(0.975, 30) == "BREACH"
    assert threshold_status(0.975, 31) == "BREACH"
    assert threshold_status(0.99, 10) == "PASS"


def test_backtesting_calibration_excludes_test_day_and_counts_apl_hpl_separately() -> None:
    pnl_rows = generate_daily_pnl()
    desk_rows = pnl_by_desk(pnl_rows)["TD-RATES"]
    sample = backtesting_sample(desk_rows)
    calibration = calibration_rows_for_date(desk_rows, sample[0]["date"])
    assert calibration[0]["date"] == "2024-09-02"
    assert calibration[-1]["date"] == "2025-08-29"
    assert sample[0]["date"] not in {row["date"] for row in calibration}
    assert all(row["date"] < sample[0]["date"] for row in calibration)
    summaries = calculate_backtesting(pnl_rows, write_artifacts=False)["summaries"]
    rates_975 = [
        row
        for row in summaries
        if row.desk_id == "TD-RATES" and row.confidence_level == 0.975
    ][0]
    assert rates_975.apl_exceptions == 5
    assert rates_975.hpl_exceptions == 5
    assert rates_975.overall_exceptions == max(
        rates_975.apl_exceptions,
        rates_975.hpl_exceptions,
    )
    assert rates_975.overall_exceptions != (
        rates_975.apl_exceptions + rates_975.hpl_exceptions
    )


def test_canonical_backtesting_results_pass_desk_thresholds(
    phase7_output: dict[str, Any],
) -> None:
    summaries = {
        (row.desk_id, row.confidence_level): row
        for row in phase7_output["backtesting"]["summaries"]
    }
    expected = {
        ("TD-RATES", 0.975): (5, 5, 5, 30),
        ("TD-RATES", 0.99): (2, 2, 2, 12),
        ("TD-EQUITY", 0.975): (4, 5, 5, 30),
        ("TD-EQUITY", 0.99): (2, 2, 2, 12),
        ("TD-FX", 0.975): (6, 6, 6, 30),
        ("TD-FX", 0.99): (2, 2, 2, 12),
    }
    for key, counts in expected.items():
        row = summaries[key]
        assert (
            row.apl_exceptions,
            row.hpl_exceptions,
            row.overall_exceptions,
            row.threshold,
        ) == counts
        assert row.threshold_status == "PASS"


def test_desk_diagnostic_logic_separates_pla_backtesting_and_nmrf_status(
    phase7_output: dict[str, Any],
) -> None:
    assert diagnostic_status_for("GREEN", "PASS", "PASS") == IMA_TEST_GATE_PASS
    assert diagnostic_status_for("AMBER", "PASS", "PASS") == PLA_AMBER_DIAGNOSTIC
    assert diagnostic_status_for("RED", "PASS", "PASS") == SA_FALLBACK_REQUIRED
    assert diagnostic_status_for("GREEN", "BREACH", "PASS") == SA_FALLBACK_REQUIRED
    diagnostics = {row.desk_id: row for row in phase7_output["diagnostics"]}
    assert diagnostics["TD-RATES"].diagnostic_status == IMA_TEST_GATE_PASS
    assert diagnostics["TD-EQUITY"].diagnostic_status == IMA_TEST_GATE_PASS
    assert diagnostics["TD-EQUITY"].nmrf_candidate_factors == "RF_EQUITY_SPX_VOL_1Y"
    assert diagnostics["TD-FX"].diagnostic_status == SA_FALLBACK_REQUIRED
    assert {row.pla_amber_capital_surcharge_status for row in diagnostics.values()} == {
        AMBER_SURCHARGE_DEFERRED
    }
    assert {row.bank_wide_ima_approval_status for row in diagnostics.values()} == {
        "NOT_ASSESSED_PHASE7"
    }


def test_governance_files_reflect_only_canonical_phase7_findings() -> None:
    diagnostics = {
        row["desk_id"]: row
        for row in _read_csv(REPO_ROOT / "governance" / "desk_ima_diagnostic.csv")
    }
    findings = _read_csv(REPO_ROOT / "governance" / "pla_backtesting_findings.csv")
    assert diagnostics["TD-FX"]["diagnostic_status"] == SA_FALLBACK_REQUIRED
    assert diagnostics["TD-RATES"]["diagnostic_status"] == IMA_TEST_GATE_PASS
    assert diagnostics["TD-EQUITY"]["diagnostic_status"] == IMA_TEST_GATE_PASS
    assert {row["desk_id"] for row in findings} == {"TD-FX"}
    assert {row["status"] for row in findings} == {"OPEN"}
    assert {row["remediation_required"] for row in findings} == {"true"}
    assert {row["finding_type"] for row in findings} == {
        "PLA_RED_SPEARMAN_AND_KS",
        "RTPL_FACTOR_GAP",
    }


def test_phase7_parameter_provenance_is_complete() -> None:
    rows = _parameter_rows()
    official = {
        "PLA_SAMPLE_OBSERVATIONS",
        "PLA_SPEARMAN_METRIC",
        "PLA_KS_METRIC",
        "PLA_KS_ECDF_INCREMENT",
        "PLA_SPEARMAN_GREEN_THRESHOLD",
        "PLA_KS_GREEN_THRESHOLD",
        "PLA_SPEARMAN_RED_THRESHOLD",
        "PLA_KS_RED_THRESHOLD",
        "HPL_STATIC_POSITION_RULE",
        "RTPL_INCLUDED_FACTOR_RULE",
        "DESK_BT_SAMPLE_OBSERVATIONS",
        "DESK_BT_VAR_975_CONFIDENCE",
        "DESK_BT_VAR_99_CONFIDENCE",
        "DESK_BT_VAR_CALIBRATION_WINDOW",
        "DESK_BT_APL_HPL_EXCEPTION_RULE",
        "DESK_BT_MISSING_DATA_OUTLIER_RULE",
        "DESK_BT_975_THRESHOLD",
        "DESK_BT_99_THRESHOLD",
        "DESK_PLA_RED_FALLBACK_RULE",
    }
    project_choices = {
        "PHASE7_SYNTHETIC_APL_CONVENTION",
        "PHASE7_HS_VAR_QUANTILE_CONVENTION",
        "PHASE7_RTPL_DESK_MODEL_SPEC",
    }
    assert official | project_choices <= set(rows)
    for parameter_id in official:
        assert rows[parameter_id]["source_id"] == "BIS_MAR32"
        assert rows[parameter_id]["source_paragraph_or_table"].startswith("MAR32")
    assert rows["DESK_BT_99_THRESHOLD"]["value"] == ">12"
    assert rows["DESK_BT_975_THRESHOLD"]["value"] == ">=30"
    stale_975_boundary = "greater than " + "30"
    assert stale_975_boundary not in rows["DESK_BT_975_THRESHOLD"]["notes"]
    assert rows["DESK_PLA_AMBER_SURCHARGE_STATUS"]["implementation_status"] == "DEFERRED"
    for parameter_id in project_choices:
        assert rows[parameter_id]["source_id"] == "PROJECT_MODEL_CHOICE"


def test_phase7_artifacts_are_ignored_and_untracked(phase7_output: dict[str, Any]) -> None:
    assert phase7_output["status"] == "PHASE7_DESK_LEVEL_DIAGNOSTICS_COMPLETE"
    paths = [
        "data/artifacts/phase7_daily_pnl.csv",
        "data/artifacts/phase7_pla_results.csv",
        "data/artifacts/phase7_backtesting_exceptions.csv",
        "data/artifacts/phase7_backtesting_results.csv",
        "data/artifacts/phase7_desk_diagnostic.csv",
    ]
    ignored = subprocess.run(
        ["git", "check-ignore", *paths],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert ignored.returncode == 0
    tracked = subprocess.run(
        ["git", "ls-files", *paths],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert tracked.stdout == ""


def test_deferred_final_or_unapproved_outputs_do_not_exist() -> None:
    forbidden = [
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "default_risk.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "capital_aggregation.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "bank_wide_multiplier.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "amber_surcharge.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "mar33_41.py",
        REPO_ROOT / "data" / "artifacts" / "nmrf_capital.csv",
        REPO_ROOT / "data" / "artifacts" / "phase7_amber_surcharge.csv",
        REPO_ROOT / "data" / "artifacts" / "phase7_bank_wide_backtesting.csv",
        REPO_ROOT / "data" / "artifacts" / "phase8_bank_capital.csv",
    ]
    assert not any(path.exists() for path in forbidden)


def test_private_files_and_positive_claim_scan_remain_clean() -> None:
    private = ["PROJECT_FRTB_V2_SPEC.md", "FRTB_V2_STATUS.md", "local_frtb_v2_baseline/"]
    ignored = subprocess.run(
        ["git", "check-ignore", *private],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert ignored.returncode == 0
    tracked = subprocess.run(
        ["git", "ls-files", *private],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert tracked.stdout == ""
    leaked_path = "/Users/" + "linruihe/"
    excluded = (
        "__pycache__/**",
        "*.pyc",
        "PROJECT_FRTB_V2_SPEC.md",
        "FRTB_V2_STATUS.md",
        "local_frtb_v2_baseline/**",
    )
    path_matches = scan_public_text(REPO_ROOT, leaked_path, excluded_globs=excluded)
    assert path_matches == []
    prohibited = [
        "regulatory " + "compliant",
        "Basel " + "compliant",
        "FRTB " + "compliant",
        "approved " + "by",
        "portfolio regulatory " + "capital",
    ]
    for phrase in prohibited:
        matches = scan_public_text(
            REPO_ROOT,
            phrase,
            case_sensitive=False,
            excluded_globs=excluded,
        )
        assert matches == [], format_matches(matches, REPO_ROOT)
