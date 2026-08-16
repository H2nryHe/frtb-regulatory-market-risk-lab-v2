from __future__ import annotations

import csv
import math
import subprocess
from pathlib import Path
from typing import Any

import pytest

from frtb_lab.ima.es import calculate_phase5_ima_es
from frtb_lab.ima.expected_shortfall import empirical_expected_shortfall
from frtb_lab.ima.liquidity_horizon import (
    factor_liquidity_horizons,
    liquidity_horizon_expected_shortfall,
    manual_liquidity_horizon_es,
    q_sets_for_factors,
)
from frtb_lab.ima.revaluation import FULL_FACTOR_IDS, portfolio_pnl_for_shock, portfolio_pnl_vector
from frtb_lab.ima.stress_calibration import (
    load_reduced_factor_config,
    reduced_factor_ids,
    select_stress_window,
    stress_scaling_ratio,
    stress_windows,
)
from frtb_lab.ima.synthetic_history import (
    current_period_shocks,
    generate_synthetic_history,
    ten_day_shocks,
)
from frtb_lab.sa.drc import calculate_non_securitisation_drc
from frtb_lab.sa.rrao import calculate_rrao
from frtb_lab.sa.standardised import calculate_selected_scope_standardised_approach

REPO_ROOT = Path(__file__).resolve().parents[1]
PARAMETER_CROSSWALK = REPO_ROOT / "regulatory" / "parameter_crosswalk.csv"
RISK_FACTOR_INVENTORY = REPO_ROOT / "governance" / "ima_risk_factor_inventory.csv"


@pytest.fixture(scope="module")
def history() -> list[dict[str, Any]]:
    return generate_synthetic_history()


@pytest.fixture(scope="module")
def ten_day_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return ten_day_shocks(history)


@pytest.fixture(scope="module")
def phase5_output() -> dict[str, Any]:
    return calculate_phase5_ima_es(write_artifacts=True)


def _parameter_rows() -> dict[str, dict[str, str]]:
    with PARAMETER_CROSSWALK.open(newline="") as handle:
        return {row["parameter_id"]: row for row in csv.DictReader(handle)}


def _inventory_rows() -> dict[str, dict[str, str]]:
    with RISK_FACTOR_INVENTORY.open(newline="") as handle:
        return {row["risk_factor_id"]: row for row in csv.DictReader(handle)}


def test_phase4_selected_scope_standardised_approach_is_unchanged() -> None:
    result = calculate_selected_scope_standardised_approach(write_artifacts=False)
    assert result["selected_sbm"] == pytest.approx(601060.6801585773)
    assert result["non_securitisation_drc"] == pytest.approx(25200.0)
    assert result["rrao"] == pytest.approx(250.0)
    assert result["selected_scope_standardised_approach_capital"] == pytest.approx(
        626510.6801585772
    )


def test_phase4_drc_and_rrao_regressions_remain_intact() -> None:
    drc = calculate_non_securitisation_drc(write_artifacts=False)
    assert drc.gross_jtd[0].gross_jtd == pytest.approx(420000.0)
    assert drc.net_jtd[0].net_long_jtd == pytest.approx(420000.0)
    assert drc.total_drc == pytest.approx(25200.0)
    rrao = calculate_rrao(write_artifact=False)
    barrier = {row.instrument_id: row for row in rrao.rows}["SYN_EQ_BARRIER"]
    assert rrao.total_rrao == pytest.approx(250.0)
    assert barrier.rrao_category == "OTHER_RESIDUAL_RISK"


def test_synthetic_history_is_deterministic_and_uses_fixed_dates(
    history: list[dict[str, Any]],
) -> None:
    duplicate = generate_synthetic_history()
    assert history == duplicate
    assert len(history) == 5119
    assert history[0]["date"] == "2007-01-02"
    assert history[-1]["date"] == "2026-08-14"
    assert any(row["date"].startswith("2007-") for row in history)


def test_synthetic_history_code_has_no_live_market_data_sources() -> None:
    prohibited = ["requests", "yfinance", "fred", "date.today", "datetime.today"]
    for token in prohibited:
        scan = subprocess.run(
            ["git", "grep", "-n", token, "--", "src/frtb_lab/ima"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert scan.returncode == 1


def test_candidate_ima_risk_factors_have_controlled_phase6_outcomes() -> None:
    rows = _inventory_rows()
    assert set(rows) == set(FULL_FACTOR_IDS)
    horizons = factor_liquidity_horizons()
    assert set(FULL_FACTOR_IDS) <= set(horizons)
    assert {row["rfet_mechanics_result"] for row in rows.values()} == {"PASS", "FAIL"}
    assert not any(row["modellability_status"] == "MODELLABLE" for row in rows.values())
    assert all(row["phase6_rfet_required"] == "true" for row in rows.values())
    assert all(row["full_set_flag"] == "true" for row in rows.values())
    assert rows["RF_FX_EURUSD_VOL_1Y"]["reduced_set_flag"] == "false"
    governance_scan = subprocess.run(
        ["git", "grep", "-n", "IMA_ELIGIBLE\\|IMA_INELIGIBLE", "--", "governance"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert governance_scan.returncode == 1


def test_ten_day_shocks_are_direct_overlapping_observations(
    history: list[dict[str, Any]],
    ten_day_history: list[dict[str, Any]],
) -> None:
    assert len(ten_day_history) == len(history) - 10
    first = ten_day_history[0]
    second = ten_day_history[1]
    assert first["start_date"] == history[0]["date"]
    assert second["start_date"] == history[1]["date"]
    assert first["RF_GIRR_USD_5Y_RATE"] == pytest.approx(
        history[10]["RF_GIRR_USD_5Y_RATE"] - history[0]["RF_GIRR_USD_5Y_RATE"]
    )
    assert first["RF_EQUITY_SPX_SPOT"] == pytest.approx(
        math.log(history[10]["RF_EQUITY_SPX_SPOT"] / history[0]["RF_EQUITY_SPX_SPOT"])
    )


def test_direct_ten_day_es_is_not_sqrt_time_scaled_from_one_day_history(
    history: list[dict[str, Any]],
) -> None:
    factors = set(FULL_FACTOR_IDS)
    direct_ten_day = empirical_expected_shortfall(
        portfolio_pnl_vector(ten_day_shocks(history), factors)
    )
    sqrt_scaled_one_day = math.sqrt(10.0) * empirical_expected_shortfall(
        portfolio_pnl_vector(ten_day_shocks(history, window_days=1), factors)
    )
    assert direct_ten_day != pytest.approx(sqrt_scaled_one_day, rel=1e-4)


def test_empirical_expected_shortfall_tail_selection_and_sign_convention() -> None:
    pnl = [-100.0, -80.0, -60.0] + [0.0] * 97
    assert empirical_expected_shortfall(pnl) == pytest.approx(80.0)
    assert empirical_expected_shortfall(list(reversed(pnl))) == pytest.approx(80.0)
    worse_pnl = [-120.0, -80.0, -60.0] + [0.0] * 97
    assert empirical_expected_shortfall(worse_pnl) > empirical_expected_shortfall(pnl)
    assert empirical_expected_shortfall([-10.0] * 100) == pytest.approx(10.0)
    adverse_equity = {factor: 0.0 for factor in FULL_FACTOR_IDS}
    adverse_equity["RF_EQUITY_SPX_SPOT"] = -0.10
    adverse_pnl = portfolio_pnl_for_shock(adverse_equity)
    assert adverse_pnl < 0.0
    assert empirical_expected_shortfall([adverse_pnl] * 40) == pytest.approx(-adverse_pnl)


def test_selected_liquidity_horizon_mapping_and_nested_q_sets() -> None:
    horizons = factor_liquidity_horizons()
    assert horizons["RF_GIRR_USD_5Y_RATE"] == 10
    assert horizons["RF_EQUITY_SPX_SPOT"] == 10
    assert horizons["RF_EQUITY_SPX_VOL_1Y"] == 20
    assert horizons["RF_FX_EURUSD_SPOT"] == 10
    assert horizons["RF_FX_EURUSD_VOL_1Y"] == 40
    assert {horizons[f"TEST_LH_{value}"] for value in [10, 20, 40, 60, 120]} == {
        10,
        20,
        40,
        60,
        120,
    }
    q_sets = q_sets_for_factors(set(FULL_FACTOR_IDS), horizons)
    assert set(q_sets[120]) <= set(q_sets[60]) <= set(q_sets[40]) <= set(q_sets[20])
    assert set(q_sets[20]) <= set(q_sets[10])
    assert "RF_FX_EURUSD_SPOT" not in q_sets[20]
    assert "RF_EQUITY_SPX_VOL_1Y" not in q_sets[40]


def test_liquidity_horizon_formula_is_manual_five_horizon_aggregation() -> None:
    factors = {f"TEST_LH_{value}" for value in [10, 20, 40, 60, 120]}
    losses = {
        "TEST_LH_10": -100.0,
        "TEST_LH_20": -20.0,
        "TEST_LH_40": -10.0,
        "TEST_LH_60": -5.0,
        "TEST_LH_120": -2.0,
    }

    def pnl_function(shocks: list[dict[str, Any]], subset: set[str]) -> list[float]:
        pnl = sum(losses[factor] for factor in subset)
        return [pnl for _ in shocks]

    result = liquidity_horizon_expected_shortfall(
        [{} for _ in range(100)],
        factors,
        factor_set_name="TEST",
        observation_period="manual",
        pnl_function=pnl_function,
    )
    expected_by_horizon = {
        10: 137.0,
        20: 37.0,
        40: 17.0,
        60: 7.0,
        120: 2.0,
    }
    assert result.es_by_horizon == expected_by_horizon
    assert result.liquidity_adjusted_es == pytest.approx(
        manual_liquidity_horizon_es(expected_by_horizon)
    )
    naive_scaling = sum(
        abs(losses[factor]) * math.sqrt(horizon / 10.0)
        for factor, horizon in factor_liquidity_horizons().items()
        if factor in losses
    )
    assert result.liquidity_adjusted_es != pytest.approx(naive_scaling)


def test_phase5_current_es_outputs_are_deterministic(phase5_output: dict[str, Any]) -> None:
    assert phase5_output["status"] == "PROVISIONAL_IMA_ES_MECHANICS"
    assert phase5_output["history_observations"] == 5119
    assert phase5_output["ten_day_observations"] == 5109
    assert phase5_output["current_observations"] == 261
    assert phase5_output["full_current"].base_10d_es == pytest.approx(134896.55796388566)
    assert phase5_output["full_current"].liquidity_adjusted_es == pytest.approx(
        135310.97891484312
    )
    assert phase5_output["reduced_current"].base_10d_es == pytest.approx(136563.38461801698)
    assert phase5_output["reduced_current"].liquidity_adjusted_es == pytest.approx(
        136600.78255244752
    )
    assert not any(
        factor.startswith("TEST_LH_")
        for q_set in phase5_output["full_current"].q_sets.values()
        for factor in q_set
    )


def test_reduced_factor_set_is_strict_subset_pending_rfet_and_coverage_pass(
    phase5_output: dict[str, Any],
) -> None:
    config = load_reduced_factor_config()
    full = set(FULL_FACTOR_IDS)
    reduced = reduced_factor_ids(config)
    assert reduced < full
    assert config["metadata"]["status"] == "PENDING_RFET_VALIDATION"
    diagnostic = phase5_output["stress_calibration"].reduced_set_diagnostic
    assert diagnostic.evaluation_weeks == 12
    assert diagnostic.minimum_ratio == pytest.approx(0.75)
    assert diagnostic.average_ratio == pytest.approx(1.0116454032543514)
    assert diagnostic.status == "PASS"


def test_stress_calibration_selects_max_reduced_set_window(
    ten_day_history: list[dict[str, Any]],
    phase5_output: dict[str, Any],
) -> None:
    windows = stress_windows(ten_day_history, reduced_factor_ids())
    selected = select_stress_window(windows)
    calibration = phase5_output["stress_calibration"]
    assert len(windows) == 232
    assert all(window.observation_count == 252 for window in windows)
    assert selected.reduced_set_es == max(window.reduced_set_es for window in windows)
    assert calibration.stress_period_start == selected.stress_period_start
    assert calibration.stress_period_end == selected.stress_period_end
    assert calibration.stress_period_start == "2008-07-28"
    assert calibration.stress_period_end == "2009-07-14"
    assert calibration.es_f_c == pytest.approx(135310.97891484312)
    assert calibration.es_r_c == pytest.approx(136600.78255244752)
    assert calibration.es_r_s == pytest.approx(377307.3028054556)
    assert calibration.raw_scaling_ratio == pytest.approx(0.9905578605517198)
    assert calibration.floored_scaling_ratio == pytest.approx(1.0)
    assert calibration.scaled_stressed_es == pytest.approx(377307.3028054556)


def test_stress_scaling_ratio_floor_and_zero_guard() -> None:
    assert stress_scaling_ratio(200.0, 100.0) == pytest.approx((2.0, 2.0))
    assert stress_scaling_ratio(50.0, 100.0) == pytest.approx((0.5, 1.0))
    assert stress_scaling_ratio(100.0, 100.0) == pytest.approx((1.0, 1.0))
    with pytest.raises(ValueError, match="ES_R_C"):
        stress_scaling_ratio(100.0, 0.0)


def test_current_period_shocks_use_configured_one_year_window(
    ten_day_history: list[dict[str, Any]],
) -> None:
    current = current_period_shocks(ten_day_history)
    assert len(current) == 261
    assert current[0]["end_date"] == "2025-08-15"
    assert current[-1]["end_date"] == "2026-08-14"


def test_phase5_parameter_provenance_is_complete() -> None:
    rows = _parameter_rows()
    official = {
        "IMA_ES_CONFIDENCE_LEVEL",
        "IMA_BASE_HORIZON_DAYS",
        "IMA_LH_GRID",
        "IMA_LH_USD_RATE",
        "IMA_LH_EQUITY_SPOT_LARGE_CAP",
        "IMA_LH_EQUITY_VOL_LARGE_CAP",
        "IMA_LH_FX_SPECIFIED_PAIR_SPOT",
        "IMA_LH_FX_VOL",
        "IMA_Q_SET_RULE",
        "IMA_LH_ES_FORMULA",
        "IMA_CURRENT_PERIOD_RULE",
        "IMA_STRESS_HISTORY_START_RULE",
        "IMA_STRESS_WINDOW_LENGTH",
        "IMA_STRESS_SCALING_FORMULA",
        "IMA_REDUCED_SET_COVERAGE_THRESHOLD",
        "IMA_REDUCED_SET_COVERAGE_PERIOD",
    }
    project_choices = {
        "IMA_EMPIRICAL_ES_TAIL_WEIGHTING",
        "IMA_SYNTHETIC_HISTORY_SEED",
        "IMA_OVERLAPPING_10D_OBSERVATIONS",
    }
    assert official | project_choices <= set(rows)
    for parameter_id in official:
        row = rows[parameter_id]
        assert row["source_id"] == "BIS_MAR33"
        assert row["source_paragraph_or_table"].startswith("MAR33")
    for parameter_id in project_choices:
        row = rows[parameter_id]
        assert row["source_id"] == "PROJECT_MODEL_CHOICE"
        assert row["implementation_status"] == "IMPLEMENTED"


def test_phase5_artifacts_are_ignored_and_untracked(phase5_output: dict[str, Any]) -> None:
    assert phase5_output["status"] == "PROVISIONAL_IMA_ES_MECHANICS"
    phase5_paths = [
        "data/artifacts/phase5_es_current.csv",
        "data/artifacts/phase5_liquidity_horizon_es.csv",
        "data/artifacts/phase5_stress_windows.csv",
        "data/artifacts/phase5_stress_calibration.csv",
        "data/artifacts/phase5_reduced_set_diagnostic.csv",
        "data/artifacts/phase5_synthetic_history.csv",
    ]
    ignored = subprocess.run(
        ["git", "check-ignore", *phase5_paths],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert ignored.returncode == 0
    tracked = subprocess.run(
        ["git", "ls-files", *phase5_paths],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert tracked.stdout == ""


def test_phase5_clean_checkout_style_calculation_does_not_require_artifacts() -> None:
    result = calculate_phase5_ima_es(write_artifacts=False)
    assert result["status"] == "PROVISIONAL_IMA_ES_MECHANICS"
    assert result["full_current"].liquidity_adjusted_es == pytest.approx(135310.97891484312)


def test_phase5_does_not_create_deferred_ima_or_phase6_components() -> None:
    forbidden = [
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "imcc.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "nmrf.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "default_risk.py",
        REPO_ROOT / "src" / "frtb_lab" / "rfet.py",
        REPO_ROOT / "src" / "frtb_lab" / "pla.py",
        REPO_ROOT / "src" / "frtb_lab" / "backtesting.py",
        REPO_ROOT / "data" / "artifacts" / "ima_capital.csv",
        REPO_ROOT / "data" / "artifacts" / "rfet.csv",
        REPO_ROOT / "data" / "artifacts" / "pla.csv",
        REPO_ROOT / "data" / "artifacts" / "backtesting.csv",
    ]
    assert not any(path.exists() for path in forbidden)


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
