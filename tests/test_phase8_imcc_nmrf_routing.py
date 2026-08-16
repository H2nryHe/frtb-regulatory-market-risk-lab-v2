from __future__ import annotations

import csv
import math
import subprocess
from pathlib import Path
from typing import Any

import pytest
from repo_scan import format_matches, scan_public_text

from frtb_lab.ima.backtesting import threshold_status
from frtb_lab.ima.capital_routing import calculate_phase8_capital_routing
from frtb_lab.ima.desk_eligibility import calculate_phase7_desk_diagnostics
from frtb_lab.ima.es import calculate_phase5_ima_es
from frtb_lab.ima.expected_shortfall import empirical_expected_shortfall
from frtb_lab.ima.imcc import (
    aggregate_imcc,
    calculate_phase8_imcc,
    eligible_modelled_factor_ids,
    phase8_reduced_set_coverage_diagnostic,
    remediated_reduced_factor_ids,
    scaled_imcc_component,
    stress_windows_for_factor_set,
)
from frtb_lab.ima.nmrf import (
    IDIOSYNCRATIC_EQUITY_ZERO_CORRELATION,
    REMAINING_NMRF,
    NMRFSpec,
    aggregate_ses,
    calculate_phase8_ses,
    canonical_nmrf_specs,
    effective_nmrf_liquidity_horizon,
    equity_vol_full_revaluation_pnl_vector,
    stress_scenario_loss,
    stress_scenarios_for_specs,
)
from frtb_lab.ima.rfet import calculate_phase6_rfet, reduced_set_rfet_audit
from frtb_lab.ima.synthetic_history import generate_synthetic_history, ten_day_shocks
from frtb_lab.sa.standardised import calculate_selected_scope_standardised_approach
from frtb_lab.sensitivities.common import load_market_state, load_yaml
from frtb_lab.sensitivities.vega import equity_option_model_vega

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _rows_by_id(path: Path, key: str) -> dict[str, dict[str, str]]:
    return {row[key]: row for row in _read_csv(path)}


@pytest.fixture(scope="module")
def phase8_imcc() -> Any:
    return calculate_phase8_imcc(write_artifacts=False)


@pytest.fixture(scope="module")
def phase8_ses() -> Any:
    return calculate_phase8_ses(write_artifacts=False)


@pytest.fixture(scope="module")
def phase8_routing() -> Any:
    return calculate_phase8_capital_routing(write_artifacts=False)


def test_phase7_regression_and_mar32_19_boundary_are_preserved() -> None:
    sa = calculate_selected_scope_standardised_approach(write_artifacts=False)
    phase5 = calculate_phase5_ima_es(write_artifacts=False)
    phase6 = calculate_phase6_rfet(write_artifacts=False)
    phase7 = calculate_phase7_desk_diagnostics(write_artifacts=False)

    assert sa["selected_scope_standardised_approach_capital"] == pytest.approx(
        626510.6801585772
    )
    calibration = phase5["stress_calibration"]
    assert calibration.es_f_c == pytest.approx(135310.97891484312)
    assert calibration.es_r_c == pytest.approx(136600.78255244752)
    assert calibration.es_r_s == pytest.approx(377307.3028054556)

    rfet = {row.risk_factor_id: row for row in phase6["results"]}
    assert rfet["RF_GIRR_USD_5Y_RATE"].passing_route == "ROUTE_1"
    assert rfet["RF_EQUITY_SPX_SPOT"].passing_route == "ROUTE_2"
    assert rfet["RF_EQUITY_SPX_VOL_1Y"].rfet_mechanics_result == "FAIL"
    assert rfet["RF_FX_EURUSD_SPOT"].rfet_mechanics_result == "FAIL"
    assert rfet["RF_FX_EURUSD_VOL_1Y"].passing_route == "ROUTE_1"

    diagnostics = {row.desk_id: row for row in phase7["diagnostics"]}
    assert diagnostics["TD-RATES"].diagnostic_status == "SIMULATED_IMA_TEST_GATE_PASS"
    assert diagnostics["TD-EQUITY"].diagnostic_status == "SIMULATED_IMA_TEST_GATE_PASS"
    assert diagnostics["TD-FX"].diagnostic_status == "SIMULATED_SA_FALLBACK_REQUIRED"
    assert threshold_status(0.99, 12) == "PASS"
    assert threshold_status(0.99, 13) == "BREACH"
    assert threshold_status(0.975, 29) == "PASS"
    assert threshold_status(0.975, 30) == "BREACH"
    assert reduced_set_rfet_audit(phase6["results"])["audit_status"] == (
        "REDUCED_SET_RFET_MECHANICS_FAIL"
    )


def test_findings_remain_open_or_pending_validation_only() -> None:
    rfet_findings = _read_csv(REPO_ROOT / "governance" / "rfet_findings.csv")
    pla_findings = _read_csv(REPO_ROOT / "governance" / "pla_backtesting_findings.csv")
    phase8_findings = _read_csv(REPO_ROOT / "governance" / "phase8_integrated_findings.csv")

    assert {row["status"] for row in rfet_findings} == {"OPEN"}
    assert {row["status"] for row in pla_findings} == {"OPEN"}
    allowed = {"OPEN", "MITIGATED_FOR_SYNTHETIC_DEMO", "REMEDIATION_IMPLEMENTED_PENDING_VALIDATION"}
    assert all(row["prior_status"] == "OPEN" for row in phase8_findings)
    assert all(row["final_status"] in allowed for row in phase8_findings)
    assert "CLOSED" not in {row["final_status"] for row in phase8_findings}
    assert (
        _rows_by_id(REPO_ROOT / "governance" / "phase8_integrated_findings.csv", "finding_id")[
            "RFET-FIND-004"
        ]["final_status"]
        == "OPEN"
    )


def test_desk_routing_freeze_and_factor_routing() -> None:
    routing = _rows_by_id(REPO_ROOT / "governance" / "phase8_desk_routing.csv", "desk_id")
    assert routing["TD-RATES"]["phase8_route"] == "SIMULATED_IMA_BRANCH"
    assert routing["TD-EQUITY"]["phase8_route"] == "SIMULATED_IMA_BRANCH"
    assert routing["TD-FX"]["phase8_route"] == "SIMULATED_SA_FALLBACK"
    assert routing["TD-CREDIT"]["phase8_route"] == "SELECTED_SA_ONLY"
    assert routing["TD-CREDIT"]["institutional_approval_status"] == "NOT_PERFORMED"

    assumptions = load_yaml(REPO_ROOT / "configs" / "ima" / "phase8_capital_demo_assumptions.yaml")
    assert assumptions["metadata"]["institutional_modellability_determination"] == "NOT_PERFORMED"
    treatments = assumptions["risk_factor_demo_treatments"]
    assert treatments["RF_GIRR_USD_5Y_RATE"]["phase8_demo_treatment"] == (
        "SIMULATED_MODELLED_FACTOR"
    )
    assert treatments["RF_EQUITY_SPX_SPOT"]["phase8_demo_treatment"] == (
        "SIMULATED_MODELLED_FACTOR"
    )
    assert treatments["RF_EQUITY_SPX_VOL_1Y"]["phase8_demo_treatment"] == "SIMULATED_NMRF"
    assert "RF_FX_EURUSD_SPOT" not in eligible_modelled_factor_ids(assumptions)
    assert "RF_FX_EURUSD_VOL_1Y" not in eligible_modelled_factor_ids(assumptions)
    assert assumptions["eligible_nmrf_set"]["factor_ids"] == ["RF_EQUITY_SPX_VOL_1Y"]
    assert assumptions["eligible_nmrf_set"]["excluded_fallback_desk_nmrf_ids"] == [
        "RF_FX_EURUSD_SPOT"
    ]


def test_capital_routing_matrix_contains_every_selected_desk_without_total_row() -> None:
    rows = _read_csv(REPO_ROOT / "governance" / "capital_routing_matrix.csv")
    assert {"TD-RATES", "TD-EQUITY", "TD-FX", "TD-CREDIT"} <= {row["desk_id"] for row in rows}
    assert not any(
        row["desk_id"] == "TOTAL" or row["phase8_capital_branch"] == "TOTAL"
        for row in rows
    )
    assert all("FINAL" not in row["scope_status"] for row in rows)

    fx_rows = [row for row in rows if row["desk_id"] == "TD-FX"]
    assert fx_rows
    assert {row["phase8_capital_branch"] for row in fx_rows} == {
        "SELECTED_SA_FALLBACK_COMPONENTS"
    }
    assert all(not row["modelled_factor_component"] for row in fx_rows)
    assert all(not row["nmrf_component"] for row in fx_rows)


def test_phase8_reduced_set_is_separate_predeclared_and_passes_coverage(
    phase8_imcc: Any,
) -> None:
    original = load_yaml(REPO_ROOT / "configs" / "ima" / "reduced_factor_set.yaml")
    remediated = load_yaml(
        REPO_ROOT / "configs" / "ima" / "phase8_remediated_reduced_factor_set.yaml"
    )

    assert original["metadata"]["config_id"] == "phase5_provisional_reduced_factor_set"
    assert original["metadata"]["status"] == "PENDING_RFET_VALIDATION"
    assert original["reduced_factor_ids"] == [
        "RF_GIRR_USD_5Y_RATE",
        "RF_EQUITY_SPX_SPOT",
        "RF_EQUITY_SPX_VOL_1Y",
        "RF_FX_EURUSD_SPOT",
    ]
    assert remediated["metadata"]["predeclared_before_phase8_metric_evaluation"] is True
    assert remediated["coverage_diagnostic"]["no_post_hoc_capital_minimisation"] is True
    assert remediated_reduced_factor_ids(remediated) == (
        "RF_GIRR_USD_5Y_RATE",
        "RF_EQUITY_SPX_SPOT",
    )
    assert set(remediated["full_modelled_factor_ids"]) == set(remediated["reduced_factor_ids"])

    diagnostic = phase8_imcc.reduced_set_diagnostic
    assert diagnostic.evaluation_weeks == 12
    assert diagnostic.minimum_ratio == pytest.approx(0.75)
    assert diagnostic.average_ratio == pytest.approx(1.0)
    assert diagnostic.status == "PASS"

    shocks = ten_day_shocks(generate_synthetic_history())
    recomputed = phase8_reduced_set_coverage_diagnostic(
        shocks,
        set(phase8_imcc.eligible_modelled_factor_ids),
        set(phase8_imcc.remediated_reduced_factor_ids),
    )
    assert recomputed == diagnostic


def test_imcc_stress_period_and_components_are_deterministic(phase8_imcc: Any) -> None:
    shocks = ten_day_shocks(generate_synthetic_history())
    windows = stress_windows_for_factor_set(
        shocks,
        set(phase8_imcc.remediated_reduced_factor_ids),
    )
    selected = max(windows, key=lambda row: row["reduced_set_es"])
    assert phase8_imcc.stress_period_start == selected["stress_period_start"]
    assert phase8_imcc.stress_period_end == selected["stress_period_end"]
    assert phase8_imcc.stress_period_start == "2008-07-28"
    assert phase8_imcc.stress_period_end == "2009-07-14"

    assert phase8_imcc.eligible_modelled_factor_ids == (
        "RF_EQUITY_SPX_SPOT",
        "RF_GIRR_USD_5Y_RATE",
    )
    assert phase8_imcc.unconstrained.imcc_component == pytest.approx(303550.439393035)
    components = {row.component_id: row for row in phase8_imcc.constrained_components}
    assert components["CONSTRAINED_INTEREST_RATE"].factor_ids == ("RF_GIRR_USD_5Y_RATE",)
    assert components["CONSTRAINED_EQUITY"].factor_ids == ("RF_EQUITY_SPX_SPOT",)
    assert components["CONSTRAINED_INTEREST_RATE"].imcc_component == pytest.approx(
        170530.01174484068
    )
    assert components["CONSTRAINED_EQUITY"].imcc_component == pytest.approx(
        243879.43336953063
    )
    assert all(
        row.stress_period_start == phase8_imcc.stress_period_start
        and row.stress_period_end == phase8_imcc.stress_period_end
        for row in phase8_imcc.constrained_components
    )
    assert phase8_imcc.unconstrained.factor_ids != components["CONSTRAINED_EQUITY"].factor_ids
    assert phase8_imcc.unconstrained.imcc_component != pytest.approx(
        components["CONSTRAINED_EQUITY"].imcc_component
    )


def test_mar33_15_imcc_formula_and_floor_fixtures(phase8_imcc: Any) -> None:
    assert scaled_imcc_component(50.0, 100.0, 200.0) == pytest.approx((0.5, 1.0, 200.0))
    assert scaled_imcc_component(150.0, 100.0, 200.0) == pytest.approx((1.5, 1.5, 300.0))
    with pytest.raises(ValueError, match="ES_R_C"):
        scaled_imcc_component(100.0, 0.0, 200.0)

    expected = 0.5 * 100.0 + (1.0 - 0.5) * (70.0 + 50.0)
    assert aggregate_imcc(100.0, [70.0, 50.0], rho=0.5) == pytest.approx(expected)
    assert phase8_imcc.rho == pytest.approx(0.5)
    independent_expected = 0.5 * phase8_imcc.unconstrained.imcc_component + 0.5 * (
        sum(row.imcc_component for row in phase8_imcc.constrained_components)
    )
    assert phase8_imcc.simulated_selected_imcc == pytest.approx(independent_expected)
    assert phase8_imcc.simulated_selected_imcc == pytest.approx(358979.94225370314)


def test_no_sa_capital_is_mixed_into_imcc(phase8_imcc: Any, phase8_routing: Any) -> None:
    sa = calculate_selected_scope_standardised_approach(write_artifacts=False)
    assert phase8_imcc.simulated_selected_imcc != pytest.approx(
        sa["selected_scope_standardised_approach_capital"]
    )
    assert phase8_routing.imcc == phase8_imcc
    assert phase8_routing.final_total_status == "NOT_CALCULATED"
    reference = [
        row
        for row in phase8_routing.sa_fallback_components
        if row.component == "WHOLE_PORTFOLIO_SELECTED_SA_REFERENCE"
    ][0]
    assert reference.completeness_status == "REFERENCE_ONLY_NOT_ADDED_TO_IMA"


def test_nmrf_scope_liquidity_horizon_and_stress_loss(phase8_ses: Any) -> None:
    assert effective_nmrf_liquidity_horizon(10) == 20
    assert effective_nmrf_liquidity_horizon(40) == 40
    assert [row.risk_factor_id for row in phase8_ses.scenarios] == ["RF_EQUITY_SPX_VOL_1Y"]
    assert phase8_ses.excluded_fallback_desk_nmrf_ids == ("RF_FX_EURUSD_SPOT",)
    scenario = phase8_ses.scenarios[0]
    assert scenario.source_liquidity_horizon == 20
    assert scenario.effective_nmrf_liquidity_horizon == 20
    assert scenario.stress_period_start == "2019-09-19"
    assert scenario.stress_period_end == "2020-09-04"
    assert scenario.stress_scenario_loss == pytest.approx(26655.82413840059)
    assert scenario.aggregation_category == REMAINING_NMRF
    assert scenario.aggregation_category != IDIOSYNCRATIC_EQUITY_ZERO_CORRELATION

    shocks = ten_day_shocks(generate_synthetic_history(), window_days=20)
    stress_rows = [
        row
        for row in shocks
        if scenario.stress_period_start <= row["end_date"] <= scenario.stress_period_end
    ]
    spec = canonical_nmrf_specs()[0]
    assert stress_scenario_loss(spec, stress_rows) == pytest.approx(
        empirical_expected_shortfall(
            equity_vol_full_revaluation_pnl_vector(stress_rows),
            confidence_level=0.975,
        )
    )


def test_nmrf_full_revaluation_is_not_vega_times_shock_only() -> None:
    state = load_market_state()
    model_vega = equity_option_model_vega(
        instrument=state["instrument_terms"]["SYN_EQ_CALL"],
        market_state=state,
    )
    shocks = ten_day_shocks(generate_synthetic_history(), window_days=20)
    row = next(item for item in shocks if abs(item["RF_EQUITY_SPX_VOL_1Y"]) > 0.01)
    full_reval = equity_vol_full_revaluation_pnl_vector([row])[0]
    vega_linear = model_vega * row["RF_EQUITY_SPX_VOL_1Y"]
    assert full_reval != pytest.approx(vega_linear, rel=1e-8)


def test_same_risk_class_nmrf_specs_share_common_stress_period() -> None:
    base = canonical_nmrf_specs()[0]
    second = NMRFSpec(
        risk_factor_id="TEST_EQUITY_VOL_2",
        desk_id="TD-EQUITY",
        risk_class="equity",
        source_liquidity_horizon=40,
        shock_source_factor_id="RF_EQUITY_SPX_VOL_1Y",
        aggregation_category=REMAINING_NMRF,
        notes="Test-only second NMRF.",
    )
    scenarios = stress_scenarios_for_specs((base, second))
    assert len(scenarios) == 2
    assert {row.risk_class for row in scenarios} == {"equity"}
    assert len({row.stress_period_start for row in scenarios}) == 1
    assert len({row.stress_period_end for row in scenarios}) == 1
    assert {row.effective_nmrf_liquidity_horizon for row in scenarios} == {20, 40}


def test_mar33_17_ses_formula_fixture_and_canonical_result(phase8_ses: Any) -> None:
    expected = math.sqrt(3.0**2 + 4.0**2) + math.sqrt(12.0**2)
    expected += math.sqrt((0.6 * 30.0) ** 2 + (1.0 - 0.6**2) * (10.0**2 + 20.0**2))
    assert aggregate_ses([3.0, 4.0], [12.0], [10.0, 20.0], rho=0.6) == pytest.approx(
        expected
    )
    assert phase8_ses.rho == pytest.approx(0.6)
    assert phase8_ses.idiosyncratic_credit_component == pytest.approx(0.0)
    assert phase8_ses.idiosyncratic_equity_component == pytest.approx(0.0)
    assert phase8_ses.remaining_nmrf_component == pytest.approx(26655.82413840059)
    assert phase8_ses.simulated_selected_ses == pytest.approx(26655.82413840059)
    assert phase8_ses.final_total_status == "NOT_CALCULATED"


def test_sa_fallback_attribution_is_traceable_and_incomplete_by_design(
    phase8_routing: Any,
) -> None:
    fallback = {
        (row.desk_id, row.component): row for row in phase8_routing.sa_fallback_components
    }
    assert fallback[("TD-FX", "FX_DELTA")].selected_capital == pytest.approx(
        225542.7953442151
    )
    assert fallback[("TD-FX", "FX_VEGA")].selected_capital == pytest.approx(38673.6331829128)
    assert fallback[("TD-FX", "FX_CURVATURE")].selected_capital == pytest.approx(0.0)
    assert fallback[("TD-CREDIT", "NON_SECURITISATION_DRC")].selected_capital == pytest.approx(
        25200.0
    )
    assert {row.completeness_status for row in phase8_routing.sa_fallback_components} == {
        "SELECTED_SA_FALLBACK_COMPONENTS",
        "REFERENCE_ONLY_NOT_ADDED_TO_IMA",
    }
    assert "FINAL_BANK_WIDE_TOTAL_CAPITAL" in phase8_routing.deferred_components


def test_parameter_crosswalk_and_report_cover_phase8_scope() -> None:
    rows = _rows_by_id(REPO_ROOT / "regulatory" / "parameter_crosswalk.csv", "parameter_id")
    official = {
        "PHASE8_MODELLABLE_FACTOR_SCOPE",
        "PHASE8_CONSTRAINED_ES_RULE",
        "PHASE8_IMCC_RHO",
        "PHASE8_IMCC_FORMULA",
        "PHASE8_NMRF_975_STRESS_STANDARD",
        "PHASE8_NMRF_COMMON_12M_STRESS_PERIOD",
        "PHASE8_NMRF_LH_MINIMUM",
        "PHASE8_SES_FORMULA",
        "PHASE8_SES_RHO",
        "PHASE8_MODEL_INELIGIBLE_SA_FALLBACK",
    }
    project = {
        "PHASE8_SYNTHETIC_NMRF_SHOCK_ESTIMATOR",
        "PHASE8_NMRF_FINITE_SAMPLE_TAIL",
        "PHASE8_DEMO_MODELLABILITY_ASSUMPTION",
        "PHASE8_REMEDIATED_REDUCED_SET",
        "PHASE8_NO_FINAL_AGGREGATE_STATUS",
    }
    assert official | project <= set(rows)
    for parameter_id in official:
        assert rows[parameter_id]["source_id"] == "BIS_MAR33"
        assert rows[parameter_id]["source_paragraph_or_table"].startswith("MAR33")
    for parameter_id in project:
        assert rows[parameter_id]["source_id"] == "PROJECT_MODEL_CHOICE"

    report = (
        REPO_ROOT / "reports" / "sections" / "integrated_ima_sa_capital_routing.md"
    ).read_text()
    for heading in [
        "## Desk Routing",
        "## IMCC Mechanics",
        "## SES Aggregation",
        "## Why No Final Total FRTB Capital Is Reported",
    ]:
        assert heading in report
    assert "NOT_CALCULATED" in report


def test_no_deferred_phase9_or_final_capital_components_exist() -> None:
    forbidden = [
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "default_risk.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "capital_aggregation.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "bank_wide_multiplier.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "amber_surcharge.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "mar33_41.py",
        REPO_ROOT / "data" / "artifacts" / "phase7_amber_surcharge.csv",
        REPO_ROOT / "data" / "artifacts" / "phase7_bank_wide_backtesting.csv",
        REPO_ROOT / "data" / "artifacts" / "phase8_bank_capital.csv",
        REPO_ROOT / "data" / "artifacts" / "ima_capital.csv",
    ]
    assert not any(path.exists() for path in forbidden)


def test_phase8_artifacts_are_ignored_untracked_and_not_required() -> None:
    summary = calculate_phase8_capital_routing(write_artifacts=False)
    assert summary.final_total_status == "NOT_CALCULATED"
    paths = [
        "data/artifacts/phase8_modelled_factor_es.csv",
        "data/artifacts/phase8_imcc.csv",
        "data/artifacts/phase8_nmrf_stress_scenarios.csv",
        "data/artifacts/phase8_ses.csv",
        "data/artifacts/phase8_capital_routing.csv",
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


def test_private_files_local_paths_and_claim_scan_are_controlled() -> None:
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
        "supervisory " + "approved",
        "regulator " + "approved",
        "IMA " + "approved",
        "regulatory " + "modellable",
        "final " + "IMA capital",
        "bank " + "capital requirement",
        "production " + "capital",
    ]
    for phrase in prohibited:
        matches = scan_public_text(
            REPO_ROOT,
            phrase,
            case_sensitive=False,
            excluded_globs=excluded,
        )
        assert matches == [], format_matches(matches, REPO_ROOT)

    total_matches = scan_public_text(
        REPO_ROOT,
        "total " + "FRTB capital",
        case_sensitive=False,
        excluded_globs=excluded,
    )
    assert total_matches
    assert all(
        "Why No Final Total FRTB Capital Is Reported" in line
        for _, _, line in total_matches
    )
