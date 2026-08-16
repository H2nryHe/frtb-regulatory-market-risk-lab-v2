"""Selected MAR33 stress calibration mechanics for Phase 5."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from frtb_lab.ima.liquidity_horizon import (
    liquidity_horizon_expected_shortfall,
)
from frtb_lab.sensitivities.common import REPO_ROOT, load_yaml

REDUCED_SET_PATH = REPO_ROOT / "configs" / "ima" / "reduced_factor_set.yaml"
STRESS_WINDOWS_ARTIFACT = REPO_ROOT / "data" / "artifacts" / "phase5_stress_windows.csv"
STRESS_CALIBRATION_ARTIFACT = REPO_ROOT / "data" / "artifacts" / "phase5_stress_calibration.csv"
REDUCED_DIAGNOSTIC_ARTIFACT = (
    REPO_ROOT / "data" / "artifacts" / "phase5_reduced_set_diagnostic.csv"
)


@dataclass(frozen=True)
class StressWindowResult:
    stress_period_start: str
    stress_period_end: str
    observation_count: int
    reduced_set_es: float


@dataclass(frozen=True)
class ReducedSetDiagnostic:
    evaluation_weeks: int
    average_ratio: float
    minimum_ratio: float
    status: str


@dataclass(frozen=True)
class StressCalibrationResult:
    es_f_c: float
    es_r_c: float
    es_r_s: float
    raw_scaling_ratio: float
    floored_scaling_ratio: float
    scaled_stressed_es: float
    stress_period_start: str
    stress_period_end: str
    candidate_window_count: int
    reduced_set_diagnostic: ReducedSetDiagnostic


def load_reduced_factor_config(path: Path = REDUCED_SET_PATH) -> dict[str, Any]:
    return load_yaml(path)


def reduced_factor_ids(config: dict[str, Any] | None = None) -> set[str]:
    cfg = config or load_reduced_factor_config()
    return set(cfg["reduced_factor_ids"])


def reduced_set_coverage_diagnostic(
    shocks: list[dict[str, Any]],
    full_factors: set[str],
    reduced_factors: set[str],
    *,
    evaluation_weeks: int = 12,
    window_observations: int = 252,
) -> ReducedSetDiagnostic:
    ratios = []
    for week in range(evaluation_weeks):
        end = len(shocks) - 1 - week * 5
        start = end - window_observations + 1
        window = shocks[start : end + 1]
        full = liquidity_horizon_expected_shortfall(
            window,
            full_factors,
            factor_set_name="FULL",
            observation_period=f"coverage_week_{week}",
        ).liquidity_adjusted_es
        reduced = liquidity_horizon_expected_shortfall(
            window,
            reduced_factors,
            factor_set_name="REDUCED",
            observation_period=f"coverage_week_{week}",
        ).liquidity_adjusted_es
        ratios.append(reduced / full if full else 0.0)
    config = load_reduced_factor_config()
    minimum = float(config["coverage_diagnostic"]["minimum_average_ratio"])
    average = sum(ratios) / len(ratios)
    status = "PASS" if average >= minimum else "REDUCED_SET_COVERAGE_FAIL"
    return ReducedSetDiagnostic(
        evaluation_weeks=evaluation_weeks,
        average_ratio=average,
        minimum_ratio=minimum,
        status=status,
    )


def stress_windows(
    shocks: list[dict[str, Any]],
    reduced_factors: set[str],
    *,
    window_observations: int = 252,
    step_observations: int = 21,
) -> list[StressWindowResult]:
    windows = []
    for start in range(0, len(shocks) - window_observations + 1, step_observations):
        window = shocks[start : start + window_observations]
        es = liquidity_horizon_expected_shortfall(
            window,
            reduced_factors,
            factor_set_name="REDUCED",
            observation_period=f"{window[0]['end_date']}:{window[-1]['end_date']}",
        ).liquidity_adjusted_es
        windows.append(
            StressWindowResult(
                stress_period_start=window[0]["end_date"],
                stress_period_end=window[-1]["end_date"],
                observation_count=len(window),
                reduced_set_es=es,
            )
        )
    return windows


def select_stress_window(windows: list[StressWindowResult]) -> StressWindowResult:
    if not windows:
        raise ValueError("No eligible stress windows.")
    return max(windows, key=lambda row: row.reduced_set_es)


def stress_scaling_ratio(es_f_c: float, es_r_c: float) -> tuple[float, float]:
    if es_r_c <= 0.0:
        raise ValueError("Cannot calculate stress scaling ratio when ES_R_C is zero.")
    raw = es_f_c / es_r_c
    return raw, max(raw, 1.0)


def calibrate_stressed_es(
    current_shocks: list[dict[str, Any]],
    all_shocks: list[dict[str, Any]],
    full_factors: set[str],
    reduced_factors: set[str],
) -> StressCalibrationResult:
    es_f_c_result = liquidity_horizon_expected_shortfall(
        current_shocks,
        full_factors,
        factor_set_name="FULL",
        observation_period="current",
    )
    es_r_c_result = liquidity_horizon_expected_shortfall(
        current_shocks,
        reduced_factors,
        factor_set_name="REDUCED",
        observation_period="current",
    )
    windows = stress_windows(all_shocks, reduced_factors)
    selected = select_stress_window(windows)
    stress_rows = [
        row
        for row in all_shocks
        if selected.stress_period_start <= row["end_date"] <= selected.stress_period_end
    ]
    es_r_s_result = liquidity_horizon_expected_shortfall(
        stress_rows,
        reduced_factors,
        factor_set_name="REDUCED",
        observation_period="stress",
    )
    raw_ratio, floored_ratio = stress_scaling_ratio(
        es_f_c_result.liquidity_adjusted_es,
        es_r_c_result.liquidity_adjusted_es,
    )
    diagnostic = reduced_set_coverage_diagnostic(all_shocks, full_factors, reduced_factors)
    return StressCalibrationResult(
        es_f_c=es_f_c_result.liquidity_adjusted_es,
        es_r_c=es_r_c_result.liquidity_adjusted_es,
        es_r_s=es_r_s_result.liquidity_adjusted_es,
        raw_scaling_ratio=raw_ratio,
        floored_scaling_ratio=floored_ratio,
        scaled_stressed_es=es_r_s_result.liquidity_adjusted_es * floored_ratio,
        stress_period_start=selected.stress_period_start,
        stress_period_end=selected.stress_period_end,
        candidate_window_count=len(windows),
        reduced_set_diagnostic=diagnostic,
    )


def write_stress_artifacts(
    windows: list[StressWindowResult],
    calibration: StressCalibrationResult,
) -> None:
    STRESS_WINDOWS_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    with STRESS_WINDOWS_ARTIFACT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(windows[0].__dict__.keys()))
        writer.writeheader()
        writer.writerows(row.__dict__ for row in windows)
    with STRESS_CALIBRATION_ARTIFACT.open("w", newline="") as handle:
        rows = [
            {
                "ES_F_C": calibration.es_f_c,
                "ES_R_C": calibration.es_r_c,
                "ES_R_S": calibration.es_r_s,
                "raw_scaling_ratio": calibration.raw_scaling_ratio,
                "floored_scaling_ratio": calibration.floored_scaling_ratio,
                "scaled_stressed_es": calibration.scaled_stressed_es,
                "stress_period_start": calibration.stress_period_start,
                "stress_period_end": calibration.stress_period_end,
                "candidate_window_count": calibration.candidate_window_count,
            }
        ]
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with REDUCED_DIAGNOSTIC_ARTIFACT.open("w", newline="") as handle:
        row = calibration.reduced_set_diagnostic.__dict__
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)
