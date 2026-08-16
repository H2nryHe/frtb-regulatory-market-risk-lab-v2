"""Synthetic MAR31 RFET mechanics for Phase 6."""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from frtb_lab.ima.revaluation import FULL_FACTOR_IDS
from frtb_lab.ima.stress_calibration import reduced_factor_ids
from frtb_lab.sensitivities.common import REPO_ROOT, load_yaml

CONFIG_PATH = REPO_ROOT / "configs" / "ima" / "rfet_observation_plan.yaml"
OBSERVATIONS_ARTIFACT = REPO_ROOT / "data" / "artifacts" / "phase6_rfet_observations.csv"
RESULTS_ARTIFACT = REPO_ROOT / "data" / "artifacts" / "phase6_rfet_results.csv"
MONITORING_ARTIFACT = (
    REPO_ROOT / "data" / "artifacts" / "phase6_rfet_monitoring_history.csv"
)
TREATMENT_ARTIFACT = (
    REPO_ROOT / "data" / "artifacts" / "phase6_factor_treatment_diagnostic.csv"
)

SIMULATED_OBSERVATION_TYPE = "SIMULATED_RFET_OBSERVATION"
RFET_PASS = "PASS"
RFET_FAIL = "FAIL"
ES_CANDIDATE = "ES_CANDIDATE_PENDING_REAL_DATA_VALIDATION"
NMRF_CANDIDATE = "NMRF_CANDIDATE"
INSTITUTIONAL_DETERMINATION = "NOT_PERFORMED"


@dataclass(frozen=True)
class RFETObservation:
    observation_id: str
    risk_factor_id: str
    represented_risk_factor_id: str
    observation_date: str
    observation_type: str
    synthetic_source_type: str
    representative_flag: bool
    verified_for_project_mechanics: bool
    rfet_bucket_id: str
    official_regulatory_real_price_definition: str
    project_synthetic_observation_type: str
    notes: str


@dataclass(frozen=True)
class Route1Result:
    risk_factor_id: str
    evaluation_date: str
    annual_unique_observation_days: int
    route1_count_pass: bool
    minimum_90d_observations: int
    worst_90d_window_start: str
    worst_90d_window_end: str
    route1_coverage_pass: bool
    route1_pass: bool


@dataclass(frozen=True)
class Route2Result:
    risk_factor_id: str
    evaluation_date: str
    previous_12m_unique_observation_days: int
    route2_pass: bool


@dataclass(frozen=True)
class RFETResult:
    risk_factor_id: str
    evaluation_date: str
    annual_unique_observation_days: int
    route1_count_pass: bool
    minimum_90d_observations: int
    worst_90d_window_start: str
    worst_90d_window_end: str
    route1_coverage_pass: bool
    route1_pass: bool
    previous_12m_unique_observation_days: int
    route2_pass: bool
    rfet_mechanics_result: str
    passing_route: str
    rfet_failure_reason: str
    model_treatment_candidate: str
    institutional_modellability_determination: str


@dataclass(frozen=True)
class MonitoringResult:
    evaluation_date: str
    risk_factor_id: str
    route1_pass: bool
    route2_pass: bool
    overall_pass: bool
    status_change: str
    notes: str


def load_rfet_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return load_yaml(path)


def generate_synthetic_rfet_observations(
    config: dict[str, Any] | None = None,
) -> list[RFETObservation]:
    cfg = config or load_rfet_config()
    observations = []
    regulatory_definition = cfg["metadata"]["official_regulatory_real_price_definition"]
    project_type = cfg["metadata"]["project_synthetic_observation_type"]
    for factor_id, pattern in cfg["observation_patterns"].items():
        mapping = cfg["risk_factor_mappings"][factor_id]
        dates = _pattern_dates(pattern)
        for index, date in enumerate(dates, start=1):
            observations.append(
                RFETObservation(
                    observation_id=f"SIM_RFET_{factor_id}_{index:03d}",
                    risk_factor_id=factor_id,
                    represented_risk_factor_id=factor_id,
                    observation_date=date.isoformat(),
                    observation_type=SIMULATED_OBSERVATION_TYPE,
                    synthetic_source_type="DETERMINISTIC_PROJECT_PLAN",
                    representative_flag=True,
                    verified_for_project_mechanics=True,
                    rfet_bucket_id=mapping["rfet_bucket_id"],
                    official_regulatory_real_price_definition=regulatory_definition,
                    project_synthetic_observation_type=project_type,
                    notes=pattern["expected_mechanics_outcome"],
                )
            )
    return observations


def evaluate_route1(
    observations: list[RFETObservation],
    risk_factor_id: str,
    evaluation_date: str | dt.date,
    config: dict[str, Any] | None = None,
) -> Route1Result:
    cfg = config or load_rfet_config()
    if risk_factor_id not in cfg["risk_factor_mappings"]:
        return _empty_route1(risk_factor_id, evaluation_date)
    end = _as_date(evaluation_date)
    start = previous_12m_start(end)
    qualifying_days = qualifying_observation_days(observations, risk_factor_id, start, end, cfg)
    count_pass = len(qualifying_days) >= int(cfg["rules"]["route1_minimum_observations"])
    worst = worst_90_day_window_count(observations, risk_factor_id, end, cfg)
    coverage_pass = worst["minimum_90d_observations"] >= int(
        cfg["rules"]["route1_minimum_observations_per_90d_window"]
    )
    return Route1Result(
        risk_factor_id=risk_factor_id,
        evaluation_date=end.isoformat(),
        annual_unique_observation_days=len(qualifying_days),
        route1_count_pass=count_pass,
        minimum_90d_observations=worst["minimum_90d_observations"],
        worst_90d_window_start=worst["worst_90d_window_start"],
        worst_90d_window_end=worst["worst_90d_window_end"],
        route1_coverage_pass=coverage_pass,
        route1_pass=count_pass and coverage_pass,
    )


def evaluate_route2(
    observations: list[RFETObservation],
    risk_factor_id: str,
    evaluation_date: str | dt.date,
    config: dict[str, Any] | None = None,
) -> Route2Result:
    cfg = config or load_rfet_config()
    end = _as_date(evaluation_date)
    if risk_factor_id not in cfg["risk_factor_mappings"]:
        return Route2Result(risk_factor_id, end.isoformat(), 0, False)
    start = previous_12m_start(end)
    qualifying_days = qualifying_observation_days(observations, risk_factor_id, start, end, cfg)
    return Route2Result(
        risk_factor_id=risk_factor_id,
        evaluation_date=end.isoformat(),
        previous_12m_unique_observation_days=len(qualifying_days),
        route2_pass=len(qualifying_days) >= int(cfg["rules"]["route2_minimum_observations"]),
    )


def evaluate_rfet(
    observations: list[RFETObservation],
    risk_factor_id: str,
    evaluation_date: str | dt.date,
    config: dict[str, Any] | None = None,
) -> RFETResult:
    cfg = config or load_rfet_config()
    route1 = evaluate_route1(observations, risk_factor_id, evaluation_date, cfg)
    route2 = evaluate_route2(observations, risk_factor_id, evaluation_date, cfg)
    if risk_factor_id not in cfg["risk_factor_mappings"]:
        result = RFET_FAIL
        passing_route = "NONE"
        reason = "UNKNOWN_RISK_FACTOR"
    else:
        result = RFET_PASS if route1.route1_pass or route2.route2_pass else RFET_FAIL
        passing_route = _passing_route(route1.route1_pass, route2.route2_pass)
        reason = _failure_reason(route1, route2)
    treatment = ES_CANDIDATE if result == RFET_PASS else NMRF_CANDIDATE
    return RFETResult(
        risk_factor_id=risk_factor_id,
        evaluation_date=route1.evaluation_date,
        annual_unique_observation_days=route1.annual_unique_observation_days,
        route1_count_pass=route1.route1_count_pass,
        minimum_90d_observations=route1.minimum_90d_observations,
        worst_90d_window_start=route1.worst_90d_window_start,
        worst_90d_window_end=route1.worst_90d_window_end,
        route1_coverage_pass=route1.route1_coverage_pass,
        route1_pass=route1.route1_pass,
        previous_12m_unique_observation_days=route2.previous_12m_unique_observation_days,
        route2_pass=route2.route2_pass,
        rfet_mechanics_result=result,
        passing_route=passing_route,
        rfet_failure_reason=reason,
        model_treatment_candidate=treatment,
        institutional_modellability_determination=INSTITUTIONAL_DETERMINATION,
    )


def calculate_phase6_rfet(write_artifacts: bool = True) -> dict[str, Any]:
    cfg = load_rfet_config()
    observations = generate_synthetic_rfet_observations(cfg)
    evaluation_date = cfg["metadata"]["evaluation_date"]
    results = [
        evaluate_rfet(observations, factor_id, evaluation_date, cfg)
        for factor_id in FULL_FACTOR_IDS
    ]
    monitoring = monthly_monitoring_history(observations, set(FULL_FACTOR_IDS), cfg)
    treatment = factor_treatment_diagnostic(results)
    if write_artifacts:
        write_observation_artifact(observations)
        write_results_artifact(results)
        write_monitoring_artifact(monitoring)
        write_treatment_artifact(treatment)
    return {
        "observations": observations,
        "results": results,
        "monitoring": monitoring,
        "treatment": treatment,
        "reduced_set_audit": reduced_set_rfet_audit(results),
        "status": "SIMULATED_RFET_MECHANICS_COMPLETE",
    }


def qualifying_observation_days(
    observations: list[RFETObservation],
    risk_factor_id: str,
    start: str | dt.date,
    end: str | dt.date,
    config: dict[str, Any] | None = None,
) -> set[dt.date]:
    cfg = config or load_rfet_config()
    if risk_factor_id not in cfg["risk_factor_mappings"]:
        return set()
    start_date = _as_date(start)
    end_date = _as_date(end)
    bucket_id = cfg["risk_factor_mappings"][risk_factor_id]["rfet_bucket_id"]
    days = set()
    for observation in observations:
        date = _as_date(observation.observation_date)
        if not start_date <= date <= end_date:
            continue
        if observation.risk_factor_id != risk_factor_id:
            continue
        if observation.represented_risk_factor_id != risk_factor_id:
            continue
        if not observation.representative_flag:
            continue
        if not observation.verified_for_project_mechanics:
            continue
        if observation.observation_type != SIMULATED_OBSERVATION_TYPE:
            continue
        if observation.rfet_bucket_id != bucket_id:
            continue
        days.add(date)
    return days


def worst_90_day_window_count(
    observations: list[RFETObservation],
    risk_factor_id: str,
    evaluation_date: str | dt.date,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or load_rfet_config()
    end = _as_date(evaluation_date)
    period_start = previous_12m_start(end)
    window_days = int(cfg["rules"]["route1_coverage_window_calendar_days"])
    latest_start = end - dt.timedelta(days=window_days - 1)
    worst_count: int | None = None
    worst_start = period_start
    current = period_start
    while current <= latest_start:
        window_end = current + dt.timedelta(days=window_days - 1)
        count = len(
            qualifying_observation_days(
                observations,
                risk_factor_id,
                current,
                window_end,
                cfg,
            )
        )
        if worst_count is None or count < worst_count:
            worst_count = count
            worst_start = current
        current += dt.timedelta(days=1)
    worst_end = worst_start + dt.timedelta(days=window_days - 1)
    return {
        "minimum_90d_observations": int(worst_count or 0),
        "worst_90d_window_start": worst_start.isoformat(),
        "worst_90d_window_end": worst_end.isoformat(),
    }


def monthly_monitoring_dates(final_evaluation_date: str | dt.date, count: int = 12) -> list[str]:
    final = _as_date(final_evaluation_date)
    dates = [_add_months(final, -offset) for offset in range(count - 1, -1, -1)]
    return [date.isoformat() for date in dates]


def monthly_monitoring_history(
    observations: list[RFETObservation],
    risk_factor_ids: set[str],
    config: dict[str, Any] | None = None,
    evaluation_dates: list[str] | None = None,
) -> list[MonitoringResult]:
    cfg = config or load_rfet_config()
    dates = evaluation_dates or monthly_monitoring_dates(cfg["metadata"]["evaluation_date"])
    rows = []
    previous_status: dict[str, bool] = {}
    for date in dates:
        for factor_id in sorted(risk_factor_ids):
            result = evaluate_rfet(observations, factor_id, date, cfg)
            overall_pass = result.rfet_mechanics_result == RFET_PASS
            if factor_id not in previous_status:
                status_change = "INITIAL"
            elif previous_status[factor_id] == overall_pass:
                status_change = "UNCHANGED"
            else:
                status_change = (
                    "FAIL_TO_PASS" if overall_pass else "PASS_TO_FAIL"
                )
            previous_status[factor_id] = overall_pass
            rows.append(
                MonitoringResult(
                    evaluation_date=date,
                    risk_factor_id=factor_id,
                    route1_pass=result.route1_pass,
                    route2_pass=result.route2_pass,
                    overall_pass=overall_pass,
                    status_change=status_change,
                    notes="Final-date pass is not evidence of continuous pass.",
                )
            )
    return rows


def factor_treatment_diagnostic(results: list[RFETResult]) -> list[dict[str, Any]]:
    rows = []
    for result in results:
        rows.append(
            {
                "risk_factor_id": result.risk_factor_id,
                "rfet_mechanics_result": result.rfet_mechanics_result,
                "model_treatment_candidate": result.model_treatment_candidate,
                "institutional_modellability_determination": (
                    result.institutional_modellability_determination
                ),
                "diagnostic_label": "SIMULATED_RFET_FILTERED_ES_DIAGNOSTIC",
                "notes": "No filtered regulatory ES or final IMA aggregate is calculated.",
            }
        )
    return rows


def reduced_set_rfet_audit(results: list[RFETResult]) -> dict[str, Any]:
    by_factor = {row.risk_factor_id: row for row in results}
    reduced = reduced_factor_ids()
    failed = sorted(
        factor_id
        for factor_id in reduced
        if by_factor[factor_id].rfet_mechanics_result == RFET_FAIL
    )
    return {
        "phase5_reduced_factor_ids": tuple(sorted(reduced)),
        "failed_reduced_factor_ids": tuple(failed),
        "audit_status": (
            "REDUCED_SET_RFET_MECHANICS_FAIL"
            if failed
            else "REDUCED_SET_RFET_MECHANICS_PASS"
        ),
        "remediation_required": "REMEDIATION_REQUIRED" if failed else "NO_REMEDIATION_REQUIRED",
        "membership_changed": False,
    }


def validate_rfet_buckets(config: dict[str, Any] | None = None) -> None:
    cfg = config or load_rfet_config()
    for family in cfg["rfet_buckets"].values():
        buckets = family["buckets"]
        for left, right in zip(buckets, buckets[1:], strict=False):
            if float(left["lower"]) >= float(right["lower"]):
                raise ValueError("RFET bucket lower bounds must be increasing.")
            if left["upper"] is None:
                raise ValueError("Only the final RFET bucket may be open-ended.")
            if float(left["upper"]) != float(right["lower"]):
                raise ValueError("RFET buckets must be contiguous and non-overlapping.")


def bucket_for_value(bucket_family: dict[str, Any], value: float) -> str:
    matches = []
    for bucket in bucket_family["buckets"]:
        lower = float(bucket["lower"])
        upper = bucket["upper"]
        if value >= lower and (upper is None or value < float(upper)):
            matches.append(bucket["bucket_id"])
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one RFET bucket for value {value}, got {matches}.")
    return matches[0]


def write_observation_artifact(observations: list[RFETObservation]) -> None:
    _write_dataclass_csv(OBSERVATIONS_ARTIFACT, observations)


def write_results_artifact(results: list[RFETResult]) -> None:
    _write_dataclass_csv(RESULTS_ARTIFACT, results)


def write_monitoring_artifact(results: list[MonitoringResult]) -> None:
    _write_dataclass_csv(MONITORING_ARTIFACT, results)


def write_treatment_artifact(rows: list[dict[str, Any]]) -> None:
    _write_dict_csv(TREATMENT_ARTIFACT, rows)


def previous_12m_start(evaluation_date: str | dt.date) -> dt.date:
    end = _as_date(evaluation_date)
    try:
        one_year_prior = end.replace(year=end.year - 1)
    except ValueError:
        one_year_prior = end.replace(year=end.year - 1, day=28)
    return one_year_prior + dt.timedelta(days=1)


def _pattern_dates(pattern: dict[str, Any]) -> list[dt.date]:
    start = _as_date(pattern["start_date"])
    count = int(pattern["count"])
    if "interval_days" in pattern:
        return [
            start + dt.timedelta(days=int(pattern["interval_days"]) * index)
            for index in range(count)
        ]
    if "interval_months" in pattern:
        return [
            _add_months(start, int(pattern["interval_months"]) * index)
            for index in range(count)
        ]
    raise ValueError(f"Unsupported RFET observation pattern: {pattern['pattern_id']}")


def _passing_route(route1_pass: bool, route2_pass: bool) -> str:
    if route1_pass and route2_pass:
        return "BOTH"
    if route1_pass:
        return "ROUTE_1"
    if route2_pass:
        return "ROUTE_2"
    return "NONE"


def _failure_reason(route1: Route1Result, route2: Route2Result) -> str:
    if route1.route1_pass or route2.route2_pass:
        return "NONE"
    if not route1.route1_count_pass:
        return "INSUFFICIENT_ANNUAL_OBSERVATIONS"
    if not route1.route1_coverage_pass and not route2.route2_pass:
        return "RFET_90D_COVERAGE_GAP"
    return "RFET_MECHANICS_FAIL"


def _empty_route1(risk_factor_id: str, evaluation_date: str | dt.date) -> Route1Result:
    end = _as_date(evaluation_date)
    return Route1Result(
        risk_factor_id=risk_factor_id,
        evaluation_date=end.isoformat(),
        annual_unique_observation_days=0,
        route1_count_pass=False,
        minimum_90d_observations=0,
        worst_90d_window_start=previous_12m_start(end).isoformat(),
        worst_90d_window_end=(
            previous_12m_start(end) + dt.timedelta(days=89)
        ).isoformat(),
        route1_coverage_pass=False,
        route1_pass=False,
    )


def _add_months(date: dt.date, months: int) -> dt.date:
    month_index = date.month - 1 + months
    year = date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(date.day, _days_in_month(year, month))
    return dt.date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (dt.date(year, month + 1, 1) - dt.timedelta(days=1)).day


def _as_date(value: str | dt.date) -> dt.date:
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(value)


def _write_dataclass_csv(path: Path, rows: list[Any]) -> None:
    _write_dict_csv(path, [asdict(row) for row in rows])


def _write_dict_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    calculate_phase6_rfet()
