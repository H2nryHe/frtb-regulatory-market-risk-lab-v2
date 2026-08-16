from __future__ import annotations

import copy
import csv
import datetime as dt
import subprocess
from pathlib import Path
from typing import Any

import pytest
from repo_scan import format_matches, scan_public_text

from frtb_lab.ima.es import calculate_phase5_ima_es
from frtb_lab.ima.revaluation import FULL_FACTOR_IDS
from frtb_lab.ima.rfet import (
    ES_CANDIDATE,
    INSTITUTIONAL_DETERMINATION,
    NMRF_CANDIDATE,
    RFETObservation,
    bucket_for_value,
    calculate_phase6_rfet,
    evaluate_rfet,
    evaluate_route1,
    evaluate_route2,
    generate_synthetic_rfet_observations,
    load_rfet_config,
    monthly_monitoring_history,
    qualifying_observation_days,
    reduced_set_rfet_audit,
    validate_rfet_buckets,
    worst_90_day_window_count,
)
from frtb_lab.ima.synthetic_history import (
    current_period_shocks,
    generate_synthetic_history,
    ten_day_shocks,
)
from frtb_lab.sa.standardised import calculate_selected_scope_standardised_approach

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def phase6_output() -> dict[str, Any]:
    return calculate_phase6_rfet(write_artifacts=True)


def _config_with_factor(factor_id: str = "TEST_FACTOR") -> dict[str, Any]:
    cfg = copy.deepcopy(load_rfet_config())
    cfg["risk_factor_mappings"][factor_id] = {
        "broad_risk_class": "test",
        "rfet_bucket_approach": "direct_scalar_no_extra_bucket",
        "rfet_bucket_id": "RFET_DIRECT_SCALAR",
    }
    return cfg


def _obs(
    factor_id: str,
    date: str,
    *,
    observation_id: str | None = None,
    represented: str | None = None,
    representative: bool = True,
    verified: bool = True,
    bucket_id: str = "RFET_DIRECT_SCALAR",
    observation_type: str = "SIMULATED_RFET_OBSERVATION",
) -> RFETObservation:
    return RFETObservation(
        observation_id=observation_id or f"OBS_{factor_id}_{date}",
        risk_factor_id=factor_id,
        represented_risk_factor_id=represented or factor_id,
        observation_date=date,
        observation_type=observation_type,
        synthetic_source_type="TEST",
        representative_flag=representative,
        verified_for_project_mechanics=verified,
        rfet_bucket_id=bucket_id,
        official_regulatory_real_price_definition="official definition stored separately",
        project_synthetic_observation_type="SIMULATED_RFET_OBSERVATION",
        notes="test fixture",
    )


def _daily_observations(
    factor_id: str,
    start: str,
    count: int,
    *,
    step_days: int = 1,
) -> list[RFETObservation]:
    start_date = dt.date.fromisoformat(start)
    return [
        _obs(
            factor_id,
            (start_date + dt.timedelta(days=step_days * index)).isoformat(),
            observation_id=f"{factor_id}_{index:03d}",
        )
        for index in range(count)
    ]


def test_phase5_regression_and_current_10_day_window_are_unchanged() -> None:
    sa = calculate_selected_scope_standardised_approach(write_artifacts=False)
    phase5 = calculate_phase5_ima_es(write_artifacts=False)
    calibration = phase5["stress_calibration"]
    history = generate_synthetic_history()
    shocks = ten_day_shocks(history)
    current = current_period_shocks(shocks)
    assert sa["selected_scope_standardised_approach_capital"] == pytest.approx(
        626510.6801585772
    )
    assert calibration.es_f_c == pytest.approx(135310.97891484312)
    assert calibration.es_r_c == pytest.approx(136600.78255244752)
    assert calibration.es_r_s == pytest.approx(377307.3028054556)
    assert calibration.raw_scaling_ratio == pytest.approx(0.9905578605517198)
    assert calibration.floored_scaling_ratio == pytest.approx(1.0)
    assert calibration.scaled_stressed_es == pytest.approx(377307.3028054556)
    assert len(history) == 5119
    assert history[0]["date"] == "2007-01-02"
    assert history[-1]["date"] == "2026-08-14"
    assert len(shocks) == 5109
    assert shocks[0]["start_date"] == "2007-01-02"
    assert shocks[0]["end_date"] == "2007-01-16"
    assert len(current) == 261
    assert current[0]["start_date"] == "2025-08-01"
    assert current[0]["end_date"] == "2025-08-15"
    assert current[-1]["start_date"] == "2026-07-31"
    assert current[-1]["end_date"] == "2026-08-14"


def test_synthetic_observation_generation_is_deterministic_and_frozen() -> None:
    cfg = load_rfet_config()
    first = generate_synthetic_rfet_observations(cfg)
    second = generate_synthetic_rfet_observations(cfg)
    assert first == second
    assert cfg["metadata"]["frozen_before_evaluation"] is True
    assert cfg["metadata"]["evaluation_date"] == "2026-08-14"
    assert len(first) == 192
    assert {row.observation_type for row in first} == {"SIMULATED_RFET_OBSERVATION"}
    assert all(
        row.project_synthetic_observation_type == "SIMULATED_RFET_OBSERVATION"
        for row in first
    )
    assert not any(row.observation_type == "REAL_PRICE" for row in first)


def test_no_network_or_live_market_source_is_used_for_rfet() -> None:
    for token in ["requests", "yfinance", "fred", "urllib", "httpx"]:
        scan = subprocess.run(
            ["git", "grep", "-n", token, "--", "src/frtb_lab/ima/rfet.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert scan.returncode == 1


def test_mapping_rejections_and_once_per_day_counting() -> None:
    cfg = _config_with_factor()
    observations = [
        _obs("TEST_FACTOR", "2026-01-01", observation_id="good1"),
        _obs("TEST_FACTOR", "2026-01-01", observation_id="same_day_duplicate"),
        _obs("TEST_FACTOR", "2026-01-02", representative=False),
        _obs("TEST_FACTOR", "2026-01-03", represented="OTHER_FACTOR"),
        _obs("TEST_FACTOR", "2026-01-04", bucket_id="WRONG_BUCKET"),
        _obs("UNKNOWN", "2026-01-05"),
    ]
    days = qualifying_observation_days(
        observations,
        "TEST_FACTOR",
        "2026-01-01",
        "2026-01-31",
        cfg,
    )
    assert days == {dt.date(2026, 1, 1)}
    unknown = evaluate_rfet(observations, "UNKNOWN", "2026-01-31", cfg)
    assert unknown.rfet_mechanics_result == "FAIL"
    assert unknown.rfet_failure_reason == "UNKNOWN_RISK_FACTOR"


def test_route1_count_threshold_and_coverage_are_independent() -> None:
    cfg = _config_with_factor()
    fail_23 = evaluate_route1(
        _daily_observations("TEST_FACTOR", "2025-08-15", 23, step_days=15),
        "TEST_FACTOR",
        "2026-08-14",
        cfg,
    )
    assert fail_23.annual_unique_observation_days == 23
    assert fail_23.route1_count_pass is False
    assert fail_23.route1_pass is False
    clustered_24 = evaluate_route1(
        _daily_observations("TEST_FACTOR", "2025-08-15", 24),
        "TEST_FACTOR",
        "2026-08-14",
        cfg,
    )
    assert clustered_24.annual_unique_observation_days == 24
    assert clustered_24.route1_count_pass is True
    assert clustered_24.route1_coverage_pass is False
    assert clustered_24.route1_pass is False


def test_90_day_calendar_window_boundaries_and_gap_detection() -> None:
    cfg = _config_with_factor()
    observations = [
        _obs("TEST_FACTOR", "2026-01-01"),
        _obs("TEST_FACTOR", "2026-01-31"),
        _obs("TEST_FACTOR", "2026-03-01"),
        _obs("TEST_FACTOR", "2026-03-31"),
    ]
    counted = qualifying_observation_days(
        observations,
        "TEST_FACTOR",
        "2026-01-01",
        "2026-03-31",
        cfg,
    )
    assert len(counted) == 4
    three = qualifying_observation_days(
        observations[:-1],
        "TEST_FACTOR",
        "2026-01-01",
        "2026-03-31",
        cfg,
    )
    assert len(three) == 3
    drought = worst_90_day_window_count(
        _daily_observations("TEST_FACTOR", "2025-08-15", 30),
        "TEST_FACTOR",
        "2026-08-14",
        cfg,
    )
    assert drought["minimum_90d_observations"] == 0
    assert drought["worst_90d_window_start"] == "2025-09-14"


def test_route2_thresholds_99_100_101() -> None:
    cfg = _config_with_factor()
    fail_99 = evaluate_route2(
        _daily_observations("TEST_FACTOR", "2025-08-15", 99),
        "TEST_FACTOR",
        "2026-08-14",
        cfg,
    )
    pass_100 = evaluate_route2(
        _daily_observations("TEST_FACTOR", "2025-08-15", 100),
        "TEST_FACTOR",
        "2026-08-14",
        cfg,
    )
    pass_101 = evaluate_route2(
        _daily_observations("TEST_FACTOR", "2025-08-15", 101),
        "TEST_FACTOR",
        "2026-08-14",
        cfg,
    )
    assert fail_99.previous_12m_unique_observation_days == 99
    assert fail_99.route2_pass is False
    assert pass_100.route2_pass is True
    assert pass_101.route2_pass is True


def test_overall_rfet_uses_route1_or_route2_logic() -> None:
    output = calculate_phase6_rfet(write_artifacts=False)
    rows = {row.risk_factor_id: row for row in output["results"]}
    assert rows["RF_GIRR_USD_5Y_RATE"].passing_route == "ROUTE_1"
    assert rows["RF_EQUITY_SPX_SPOT"].passing_route == "ROUTE_2"
    assert rows["RF_EQUITY_SPX_VOL_1Y"].rfet_mechanics_result == "FAIL"
    assert rows["RF_EQUITY_SPX_VOL_1Y"].rfet_failure_reason == "INSUFFICIENT_ANNUAL_OBSERVATIONS"
    assert rows["RF_FX_EURUSD_SPOT"].annual_unique_observation_days == 24
    assert rows["RF_FX_EURUSD_SPOT"].rfet_failure_reason == "RFET_90D_COVERAGE_GAP"
    assert rows["RF_FX_EURUSD_VOL_1Y"].passing_route == "ROUTE_1"


def test_rfet_buckets_are_sourced_non_overlapping_and_not_sbm_buckets() -> None:
    cfg = load_rfet_config()
    validate_rfet_buckets(cfg)
    ir_family = cfg["rfet_buckets"]["IR_MATURITY_ROW_A"]
    vol_family = cfg["rfet_buckets"]["VOL_EXPIRY_ROW_C"]
    assert bucket_for_value(ir_family, 5.0) == "RFET_IR_A_4"
    assert bucket_for_value(vol_family, 1.0) == "RFET_VOL_C_1"
    assert all(
        "SBM" not in bucket["bucket_id"]
        for family in cfg["rfet_buckets"].values()
        for bucket in family["buckets"]
    )
    assert cfg["risk_factor_mappings"]["RF_GIRR_USD_5Y_RATE"]["rfet_bucket_id"] == "RFET_IR_A_4"
    assert cfg["risk_factor_mappings"]["RF_EQUITY_SPX_VOL_1Y"]["rfet_bucket_id"] == "RFET_VOL_C_1"


def test_monthly_monitoring_is_deterministic_and_records_no_continuous_pass_inference(
    phase6_output: dict[str, Any],
) -> None:
    first = phase6_output["monitoring"]
    second = calculate_phase6_rfet(write_artifacts=False)["monitoring"]
    assert first == second
    assert len(first) == 60
    assert {row.evaluation_date for row in first} == {
        "2025-09-14",
        "2025-10-14",
        "2025-11-14",
        "2025-12-14",
        "2026-01-14",
        "2026-02-14",
        "2026-03-14",
        "2026-04-14",
        "2026-05-14",
        "2026-06-14",
        "2026-07-14",
        "2026-08-14",
    }
    final_girr = [
        row
        for row in first
        if row.risk_factor_id == "RF_GIRR_USD_5Y_RATE"
        and row.evaluation_date == "2026-08-14"
    ][0]
    assert final_girr.overall_pass is True
    assert any("not evidence of continuous pass" in row.notes for row in first)


def test_pass_fail_pass_monitoring_fixture_records_transitions() -> None:
    cfg = _config_with_factor()
    observations = [
        *_daily_observations("TEST_FACTOR", "2025-01-01", 100),
        *_daily_observations("TEST_FACTOR", "2026-09-01", 100),
    ]
    history = monthly_monitoring_history(
        observations,
        {"TEST_FACTOR"},
        cfg,
        evaluation_dates=["2025-12-31", "2026-06-30", "2026-12-31"],
    )
    assert [row.overall_pass for row in history] == [True, False, True]
    assert [row.status_change for row in history] == [
        "INITIAL",
        "PASS_TO_FAIL",
        "FAIL_TO_PASS",
    ]


def test_qualitative_assessment_and_candidate_classification_files_exist() -> None:
    assessment_path = REPO_ROOT / "governance" / "modellability_principles_assessment.csv"
    with assessment_path.open(newline="") as handle:
        assessment = list(csv.DictReader(handle))
    assert {row["risk_factor_id"] for row in assessment} == set(FULL_FACTOR_IDS)
    assert len(assessment) == 35
    assert {row["institutional_verification_required"] for row in assessment} == {"true"}
    assert not any(row["assessment_status"] == "FINAL_MODELLABLE" for row in assessment)
    inventory_path = REPO_ROOT / "governance" / "ima_risk_factor_inventory.csv"
    with inventory_path.open(newline="") as handle:
        inventory = {row["risk_factor_id"]: row for row in csv.DictReader(handle)}
    assert all(
        row["institutional_modellability_determination"] == INSTITUTIONAL_DETERMINATION
        for row in inventory.values()
    )
    assert inventory["RF_EQUITY_SPX_VOL_1Y"]["modellability_status"] == NMRF_CANDIDATE
    assert inventory["RF_GIRR_USD_5Y_RATE"]["modellability_status"] == ES_CANDIDATE


def test_nmrf_candidates_and_reduced_set_audit_preserve_phase5_membership(
    phase6_output: dict[str, Any],
) -> None:
    results = {row.risk_factor_id: row for row in phase6_output["results"]}
    audit = reduced_set_rfet_audit(phase6_output["results"])
    assert audit["phase5_reduced_factor_ids"] == (
        "RF_EQUITY_SPX_SPOT",
        "RF_EQUITY_SPX_VOL_1Y",
        "RF_FX_EURUSD_SPOT",
        "RF_GIRR_USD_5Y_RATE",
    )
    assert audit["failed_reduced_factor_ids"] == (
        "RF_EQUITY_SPX_VOL_1Y",
        "RF_FX_EURUSD_SPOT",
    )
    assert audit["audit_status"] == "REDUCED_SET_RFET_MECHANICS_FAIL"
    assert audit["remediation_required"] == "REMEDIATION_REQUIRED"
    assert audit["membership_changed"] is False
    nmrf_path = REPO_ROOT / "governance" / "nmrf_candidate_inventory.csv"
    with nmrf_path.open(newline="") as handle:
        candidates = {row["risk_factor_id"]: row for row in csv.DictReader(handle)}
    assert set(candidates) == {
        factor_id
        for factor_id, row in results.items()
        if row.rfet_mechanics_result == "FAIL"
    }
    assert {row["stress_scenario_capital_status"] for row in candidates.values()} == {"DEFERRED"}


def test_rfet_findings_are_open_and_include_required_failure_conditions() -> None:
    with (REPO_ROOT / "governance" / "rfet_findings.csv").open(newline="") as handle:
        findings = list(csv.DictReader(handle))
    types = {row["finding_type"] for row in findings}
    assert "RFET_INSUFFICIENT_OBSERVATIONS" in types
    assert "RFET_90D_COVERAGE_GAP" in types
    assert "REDUCED_SET_RFET_CONFLICT" in types
    assert "QUALITATIVE_DATA_EVIDENCE_LIMITATION" in types
    assert {row["status"] for row in findings} == {"OPEN"}
    assert all(row["remediation_required"] == "true" for row in findings)


def test_no_deferred_final_or_unapproved_ima_components_exist() -> None:
    forbidden = [
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "default_risk.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "capital_aggregation.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "bank_wide_multiplier.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "amber_surcharge.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "mar33_41.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "phase8.py",
        REPO_ROOT / "data" / "artifacts" / "ima_capital.csv",
        REPO_ROOT / "data" / "artifacts" / "phase8_bank_capital.csv",
        REPO_ROOT / "data" / "artifacts" / "phase7_amber_surcharge.csv",
        REPO_ROOT / "data" / "artifacts" / "phase7_bank_wide_backtesting.csv",
    ]
    assert not any(path.exists() for path in forbidden)


def test_phase6_parameter_provenance_is_complete() -> None:
    with (REPO_ROOT / "regulatory" / "parameter_crosswalk.csv").open(newline="") as handle:
        rows = {row["parameter_id"]: row for row in csv.DictReader(handle)}
    required = {
        "RFET_ACCEPTABLE_PRICE_CONCEPT",
        "RFET_REPRESENTATIVENESS_MAPPING",
        "RFET_ROUTE1_MIN_OBSERVATIONS",
        "RFET_ROUTE1_90D_MIN_OBSERVATIONS",
        "RFET_ROUTE1_90D_WINDOW",
        "RFET_ROUTE2_MIN_OBSERVATIONS",
        "RFET_ONCE_PER_DAY_COUNT_RULE",
        "RFET_QUARTERLY_EVALUATION_RULE",
        "RFET_ROUTE1_MONTHLY_MONITORING_RULE",
        "RFET_BUCKET_IR_ROW_A",
        "RFET_BUCKET_VOL_EXPIRY_ROW_C",
        "RFET_SINGLE_BUCKET_COUNT_RULE",
        "RFET_PARAMETRIC_CURVE_SURFACE_RULE",
        "RFET_EQUITY_SYSTEMATIC_FACTOR_RULE",
        "RFET_CALIBRATION_DATA_DISTINCTION",
        "RFET_QUALITATIVE_PRINCIPLES",
    }
    assert required <= set(rows)
    for parameter_id in required:
        assert rows[parameter_id]["source_id"] == "BIS_MAR31"
        assert rows[parameter_id]["source_paragraph_or_table"].startswith("MAR31")
        assert rows[parameter_id]["implementation_status"] == "IMPLEMENTED"


def test_phase6_artifacts_are_ignored_untracked_and_not_required() -> None:
    result = calculate_phase6_rfet(write_artifacts=False)
    assert result["status"] == "SIMULATED_RFET_MECHANICS_COMPLETE"
    paths = [
        "data/artifacts/phase6_rfet_results.csv",
        "data/artifacts/phase6_rfet_monitoring_history.csv",
        "data/artifacts/phase6_rfet_observations.csv",
        "data/artifacts/phase6_factor_treatment_diagnostic.csv",
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


def test_private_files_and_claim_scans() -> None:
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
        "supervisory " + "approval",
        "regulatory " + "modellable",
        "Basel " + "modellable",
        "certified " + "modellable",
        "full " + "IMA",
        "IMA " + "eligible",
        "regulatory " + "IMA capital",
    ]
    for phrase in prohibited:
        matches = scan_public_text(
            REPO_ROOT,
            phrase,
            case_sensitive=False,
            excluded_globs=excluded,
        )
        if phrase == "supervisory " + "approval" and matches:
            assert format_matches(matches, REPO_ROOT).strip().endswith(
                "reports/sections/integrated_ima_sa_capital_routing.md:38:"
                "is not an institutional modellability determination, supervisory "
                "approval, or a"
            )
        else:
            assert matches == [], format_matches(matches, REPO_ROOT)
