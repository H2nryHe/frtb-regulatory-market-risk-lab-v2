from __future__ import annotations

import csv
import math
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from frtb_lab.sa.aggregation import (
    _across_bucket_capital,
    bucket_capital,
    net_sensitivities,
    risk_class_capital,
)
from frtb_lab.sa.correlations import (
    curvature_correlation,
    equity_cross_bucket_gamma,
    equity_delta_rho,
    fx_cross_bucket_gamma,
    girr_cross_bucket_gamma,
    girr_delta_rho,
    scenario_correlation,
    vega_maturity_correlation,
)
from frtb_lab.sa.curvature import curvature_capital, selected_curvature_records
from frtb_lab.sa.sbm import ARTIFACTS, calculate_selected_scope_sbm
from frtb_lab.sensitivities.common import load_market_state, load_parameters
from frtb_lab.sensitivities.equity import equity_spot_delta_sensitivity
from frtb_lab.sensitivities.generate import generate_phase2_sensitivities

REPO_ROOT = Path(__file__).resolve().parents[1]
COVERAGE_PATH = REPO_ROOT / "governance" / "sbm_sensitivity_coverage.csv"
PARAMETER_CROSSWALK = REPO_ROOT / "regulatory" / "parameter_crosswalk.csv"
PORTFOLIO_PATH = REPO_ROOT / "data" / "fixtures" / "canonical_portfolio.yaml"


def _record(
    *,
    risk_class: str = "EQUITY",
    sensitivity_type: str = "delta",
    bucket: str = "EQUITY_BUCKET_12",
    risk_factor_id: str = "RF_A",
    raw: float,
    risk_weight: float = 1.0,
    option_maturity: float | str = "",
) -> dict:
    return {
        "risk_class": risk_class,
        "sensitivity_type": sensitivity_type,
        "bucket": bucket,
        "risk_factor_id": risk_factor_id,
        "raw_sensitivity": raw,
        "risk_weight": risk_weight,
        "weighted_sensitivity": raw * risk_weight,
        "option_maturity": option_maturity,
    }


def _coverage_rows() -> list[dict[str, str]]:
    with COVERAGE_PATH.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _parameter_rows() -> dict[str, dict[str, str]]:
    with PARAMETER_CROSSWALK.open(newline="") as handle:
        return {row["parameter_id"]: row for row in csv.DictReader(handle)}


def test_bucket_12_assumption_is_documented() -> None:
    parameters = load_parameters()
    assumption = parameters["equity"]["selected_bucket"]["synthetic_assumption"]
    assert "large-cap advanced-economy constituents" in assumption
    assert "SYN_SPX_INDEX" in assumption
    assert parameters["equity"]["selected_bucket"]["bucket_id"] == "EQUITY_BUCKET_12"


def test_equity_repo_rate_is_proven_non_applicable_to_pricing() -> None:
    base_state = load_market_state()
    changed_state = deepcopy(base_state)
    changed_state["equity"]["SYN_SPX_INDEX"]["repo_rate"] = 0.99
    for instrument_id in ["SYN_EQ_INDEX", "SYN_EQ_CALL"]:
        kwargs = {
            "instrument_id": instrument_id,
            "instrument": base_state["instrument_terms"][instrument_id],
            "market_state": base_state,
        }
        changed_kwargs = {**kwargs, "market_state": changed_state}
        assert equity_spot_delta_sensitivity(**kwargs) == pytest.approx(
            equity_spot_delta_sensitivity(**changed_kwargs)
        )
    coverage = {
        (row["instrument_id"], row["pricing_risk_input"]): row for row in _coverage_rows()
    }
    assert coverage[("SYN_EQ_INDEX", "equity repo rate")]["scope_status"] == "NOT_APPLICABLE"
    assert coverage[("SYN_EQ_CALL", "equity repo rate")]["scope_status"] == "NOT_APPLICABLE"


def test_coverage_table_contains_every_canonical_instrument_and_material_input() -> None:
    with PORTFOLIO_PATH.open() as handle:
        portfolio = yaml.safe_load(handle)
    instrument_ids = {row["instrument_id"] for row in portfolio["instruments"]}
    coverage = _coverage_rows()
    assert instrument_ids <= {row["instrument_id"] for row in coverage}
    expected_inputs = {
        ("SYN_EURUSD_FWD", "USD discount rate"),
        ("SYN_EURUSD_FWD", "EUR discount rate"),
        ("SYN_EURUSD_CALL", "USD discount rate"),
        ("SYN_EURUSD_CALL", "EUR discount rate"),
        ("SYN_EQ_CALL", "USD risk-free rate"),
        ("SYN_EQ_CALL", "dividend yield"),
        ("SYN_CORP_BOND", "issuer credit spread"),
        ("SYN_EQ_BARRIER", "equity spot"),
        ("SYN_EQ_BARRIER", "equity implied volatility"),
    }
    observed = {(row["instrument_id"], row["pricing_risk_input"]) for row in coverage}
    assert expected_inputs <= observed
    assert all(row["scope_status"] for row in coverage)


def test_same_risk_factor_nets_before_risk_weighting() -> None:
    records = [
        _record(risk_factor_id="RF_NET", raw=100.0, risk_weight=0.2),
        _record(risk_factor_id="RF_NET", raw=-100.0, risk_weight=0.2),
    ]
    netted = net_sensitivities(records)
    assert len(netted) == 1
    assert netted[0]["raw_sensitivity"] == pytest.approx(0.0)
    assert netted[0]["weighted_sensitivity"] == pytest.approx(0.0)
    assert risk_class_capital(netted, "MEDIUM")["risk_class_capital"] == pytest.approx(0.0)


def test_one_risk_factor_bucket_capital_equals_absolute_weighted_sensitivity() -> None:
    result = bucket_capital([_record(raw=-125.0)], "MEDIUM")
    assert result["k_b"] == pytest.approx(125.0)


def test_two_risk_factors_same_bucket_matches_manual_formula() -> None:
    records = [_record(risk_factor_id="RF_A", raw=100.0), _record(risk_factor_id="RF_B", raw=50.0)]
    result = bucket_capital(records, "MEDIUM")
    expected = math.sqrt(100.0**2 + 50.0**2 + 2.0 * 0.80 * 100.0 * 50.0)
    assert result["k_b"] == pytest.approx(expected)


def test_across_bucket_aggregation_matches_manual_formula() -> None:
    records = [
        _record(bucket="EQUITY_BUCKET_12", risk_factor_id="RF_A", raw=100.0),
        _record(bucket="EQUITY_BUCKET_14", risk_factor_id="RF_B", raw=80.0),
    ]
    result = risk_class_capital(records, "MEDIUM")
    expected = math.sqrt(100.0**2 + 80.0**2 + 2.0 * 0.45 * 100.0 * 80.0)
    assert result["risk_class_capital"] == pytest.approx(expected)
    assert result["alternative_used"] is False


def test_negative_across_bucket_case_uses_alternative_rule() -> None:
    bucket_results = {
        "EQUITY_BUCKET_12": {"k_b": math.sqrt(20_000.0), "s_b": 200.0},
        "EQUITY_BUCKET_13": {"k_b": math.sqrt(20_000.0), "s_b": -200.0},
    }
    normal_capital, normal_radicand, _ = _across_bucket_capital(
        bucket_results, "EQUITY", "MEDIUM", use_alternative=False
    )
    alternative_capital, alternative_radicand, alternative_used = _across_bucket_capital(
        bucket_results, "EQUITY", "MEDIUM", use_alternative=True
    )
    assert normal_capital == pytest.approx(0.0)
    assert normal_radicand < 0.0
    assert alternative_used is True
    assert alternative_radicand == pytest.approx(10_000.0)
    assert alternative_capital == pytest.approx(100.0)


def test_medium_correlations_match_frozen_selected_parameters() -> None:
    assert girr_delta_rho(1.0, 5.0) == pytest.approx(0.887)
    assert girr_delta_rho(5.0, 10.0) == pytest.approx(0.970)
    assert girr_delta_rho(5.0, 5.0, same_curve=False) == pytest.approx(0.999)
    assert girr_cross_bucket_gamma() == pytest.approx(0.50)
    assert equity_delta_rho("EQUITY_BUCKET_12") == pytest.approx(0.80)
    assert equity_delta_rho("EQUITY_BUCKET_13") == pytest.approx(0.80)
    assert equity_cross_bucket_gamma("EQUITY_BUCKET_12", "EQUITY_BUCKET_13") == pytest.approx(
        0.75
    )
    assert equity_cross_bucket_gamma("EQUITY_BUCKET_12", "EQUITY_BUCKET_14") == pytest.approx(
        0.45
    )
    assert fx_cross_bucket_gamma() == pytest.approx(0.60)


def test_high_low_scenario_transformations_and_caps() -> None:
    assert scenario_correlation(0.90, "HIGH") == pytest.approx(1.0)
    assert scenario_correlation(0.80, "HIGH") == pytest.approx(1.0)
    assert scenario_correlation(0.80, "LOW") == pytest.approx(0.60)
    assert scenario_correlation(0.20, "LOW") == pytest.approx(0.15)
    assert scenario_correlation(0.50, "MEDIUM") == pytest.approx(0.50)


def test_low_medium_high_outputs_are_independently_reproducible() -> None:
    records = [_record(risk_factor_id="RF_A", raw=100.0), _record(risk_factor_id="RF_B", raw=50.0)]
    low = bucket_capital(records, "LOW")["k_b"]
    medium = bucket_capital(records, "MEDIUM")["k_b"]
    high = bucket_capital(records, "HIGH")["k_b"]
    assert low == pytest.approx(math.sqrt(100.0**2 + 50.0**2 + 2.0 * 0.60 * 100.0 * 50.0))
    assert medium == pytest.approx(math.sqrt(100.0**2 + 50.0**2 + 2.0 * 0.80 * 100.0 * 50.0))
    assert high == pytest.approx(math.sqrt(100.0**2 + 50.0**2 + 2.0 * 1.00 * 100.0 * 50.0))
    assert low < medium < high


def test_vega_maturity_correlation_and_two_maturity_fixture() -> None:
    maturity = math.exp(-0.01 * abs(1.0 - 3.0) / 1.0)
    assert vega_maturity_correlation(1.0, 3.0) == pytest.approx(maturity)
    records = [
        _record(
            sensitivity_type="vega",
            risk_factor_id="RF_VOL_1Y",
            raw=100.0,
            option_maturity=1.0,
        ),
        _record(sensitivity_type="vega", risk_factor_id="RF_VOL_3Y", raw=40.0, option_maturity=3.0),
    ]
    result = bucket_capital(records, "MEDIUM")
    expected_rho = 0.80 * maturity
    expected = math.sqrt(100.0**2 + 40.0**2 + 2.0 * expected_rho * 100.0 * 40.0)
    assert result["k_b"] == pytest.approx(expected)


def test_scenario_execution_does_not_mutate_sensitivities_or_weights() -> None:
    source = [
        _record(risk_factor_id="RF_A", raw=100.0, risk_weight=0.2),
        _record(risk_factor_id="RF_B", raw=50.0, risk_weight=0.3),
    ]
    netted = net_sensitivities(source)
    before_source = deepcopy(source)
    before_netted = deepcopy(netted)
    for scenario in ["LOW", "MEDIUM", "HIGH"]:
        risk_class_capital(netted, scenario)
    assert source == before_source
    assert netted == before_netted


def test_selected_scope_sbm_totals_equal_component_sums_and_final_max() -> None:
    output = calculate_selected_scope_sbm(write_artifacts=True)
    totals = []
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
        assert row["selected_scope_sbm_total"] == pytest.approx(component_sum)
        totals.append(row["selected_scope_sbm_total"])
    assert output["selected_scope_sbm_capital"] == pytest.approx(max(totals))


def test_curvature_records_use_full_revaluation_and_remove_delta_once() -> None:
    records = selected_curvature_records()
    assert {row["instrument_id"] for row in records} == {"SYN_EQ_CALL", "SYN_EURUSD_CALL"}
    assert "SYN_EQ_INDEX" not in {row["instrument_id"] for row in records}
    for row in records:
        shock = row["shock"]
        assert row["cvr_up"] == pytest.approx(
            -(row["up_value"] - row["base_value"] - row["delta_sensitivity"] * shock)
        )
        assert row["cvr_down"] == pytest.approx(
            -(row["down_value"] - row["base_value"] + row["delta_sensitivity"] * shock)
        )
        assert row["cvr_up"] <= 0.0
        assert row["cvr_down"] <= 0.0


def test_curvature_correlation_uses_squared_delta_correlation() -> None:
    assert curvature_correlation(0.80, "MEDIUM") == pytest.approx(0.64)
    records = [
        {
            "risk_class": "EQUITY",
            "bucket": "EQUITY_BUCKET_12",
            "risk_factor_id": "RF_A",
            "cvr_up": 100.0,
            "cvr_down": 0.0,
        },
        {
            "risk_class": "EQUITY",
            "bucket": "EQUITY_BUCKET_12",
            "risk_factor_id": "RF_B",
            "cvr_up": 100.0,
            "cvr_down": 0.0,
        },
    ]
    result = curvature_capital(records, "MEDIUM")
    expected = math.sqrt(100.0**2 + 100.0**2 + 2.0 * 0.64 * 100.0 * 100.0)
    assert result["risk_class_capital"] == pytest.approx(expected)


def test_curvature_bucket_direction_can_differ_by_scenario() -> None:
    records = [
        {
            "risk_class": "EQUITY",
            "bucket": "EQUITY_BUCKET_12",
            "risk_factor_id": "RF_A",
            "cvr_up": 100.0,
            "cvr_down": 175.0,
        },
        {
            "risk_class": "EQUITY",
            "bucket": "EQUITY_BUCKET_12",
            "risk_factor_id": "RF_B",
            "cvr_up": 100.0,
            "cvr_down": -10.0,
        },
    ]
    low_bucket = curvature_capital(records, "LOW")["bucket_results"][0]
    medium_bucket = curvature_capital(records, "MEDIUM")["bucket_results"][0]
    high_bucket = curvature_capital(records, "HIGH")["bucket_results"][0]
    assert low_bucket["selected_direction"] == "down"
    assert medium_bucket["selected_direction"] == "up"
    assert high_bucket["selected_direction"] == "up"


def test_implemented_correlation_and_curvature_parameters_have_provenance() -> None:
    rows = _parameter_rows()
    required = {
        "SBM_WITHIN_BUCKET_FORMULA",
        "SBM_ACROSS_BUCKET_FORMULA",
        "SBM_ACROSS_BUCKET_ALTERNATIVE_RULE",
        "SBM_HIGH_CORRELATION_TRANSFORM",
        "SBM_LOW_CORRELATION_TRANSFORM",
        "SBM_SCENARIO_MAX_RULE",
        "GIRR_RHO_SAME_TENOR_DIFFERENT_CURVES",
        "GIRR_RHO_1Y_5Y",
        "GIRR_RHO_5Y_10Y",
        "GIRR_GAMMA_CROSS_CURRENCY",
        "EQUITY_RHO_INDEX_BUCKETS",
        "EQUITY_GAMMA_12_13",
        "EQUITY_GAMMA_OTHER",
        "FX_GAMMA_CROSS_BUCKET",
        "VEGA_MATURITY_ALPHA",
        "VEGA_MATURITY_CORRELATION_FORMULA",
        "CURVATURE_EQUITY_FX_SHOCK_LINKED_TO_DELTA_RW",
        "CURVATURE_CORRELATION_SQUARED_DELTA",
        "CURVATURE_FULL_REVALUATION_FORMULA",
    }
    assert required <= set(rows)
    for parameter_id in required:
        row = rows[parameter_id]
        assert row["implementation_status"] == "IMPLEMENTED"
        assert row["source_id"] == "BIS_MAR21"
        assert row["source_paragraph_or_table"].startswith("MAR21")


def test_no_out_of_scope_drc_rrao_or_ima_calculations_exist() -> None:
    forbidden = [
        REPO_ROOT / "src" / "frtb_lab" / "sa" / "securitisation_drc.py",
        REPO_ROOT / "src" / "frtb_lab" / "sa" / "ctp.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "imcc.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "nmrf.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "default_risk.py",
        REPO_ROOT / "data" / "artifacts" / "drc_capital.csv",
        REPO_ROOT / "data" / "artifacts" / "rrao_capital.csv",
        REPO_ROOT / "data" / "artifacts" / "ima_capital.csv",
    ]
    assert not any(path.exists() for path in forbidden)


def test_generated_phase3_artifacts_are_ignored_and_untracked() -> None:
    calculate_selected_scope_sbm(write_artifacts=True)
    paths = [str(path.relative_to(REPO_ROOT)) for path in ARTIFACTS.values()]
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


def test_private_control_files_remain_ignored_and_untracked() -> None:
    paths = ["PROJECT_FRTB_V2_SPEC.md", "FRTB_V2_STATUS.md", "local_frtb_v2_baseline/"]
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


def test_tracked_files_have_no_local_absolute_path_or_positive_claims() -> None:
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


def test_phase2_generation_still_produces_no_capital_columns(tmp_path: Path) -> None:
    artifact = tmp_path / "phase2.csv"
    rows = generate_phase2_sensitivities(artifact)
    assert len(rows) == 8
    assert all("capital" not in key.lower() for row in rows for key in row)
