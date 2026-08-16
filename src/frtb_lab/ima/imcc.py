"""Selected Phase 8 MAR33.13-MAR33.15 IMCC mechanics."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from frtb_lab.ima.liquidity_horizon import (
    LiquidityHorizonESResult,
    liquidity_horizon_expected_shortfall,
)
from frtb_lab.ima.synthetic_history import (
    current_period_shocks,
    generate_synthetic_history,
    ten_day_shocks,
)
from frtb_lab.sensitivities.common import REPO_ROOT, load_yaml

ASSUMPTIONS_PATH = REPO_ROOT / "configs" / "ima" / "phase8_capital_demo_assumptions.yaml"
REMEDIATED_REDUCED_SET_PATH = (
    REPO_ROOT / "configs" / "ima" / "phase8_remediated_reduced_factor_set.yaml"
)
MODELLED_ES_ARTIFACT = REPO_ROOT / "data" / "artifacts" / "phase8_modelled_factor_es.csv"
IMCC_ARTIFACT = REPO_ROOT / "data" / "artifacts" / "phase8_imcc.csv"


@dataclass(frozen=True)
class Phase8ReducedSetDiagnostic:
    evaluation_weeks: int
    average_ratio: float
    minimum_ratio: float
    status: str


@dataclass(frozen=True)
class IMCCComponent:
    component_id: str
    factor_ids: tuple[str, ...]
    es_f_c: float
    es_r_c: float
    es_r_s: float
    raw_scaling_ratio: float
    floored_scaling_ratio: float
    imcc_component: float
    stress_period_start: str
    stress_period_end: str


@dataclass(frozen=True)
class IMCCResult:
    eligible_modelled_factor_ids: tuple[str, ...]
    remediated_reduced_factor_ids: tuple[str, ...]
    stress_period_start: str
    stress_period_end: str
    unconstrained: IMCCComponent
    constrained_components: tuple[IMCCComponent, ...]
    rho: float
    constrained_sum: float
    simulated_selected_imcc: float
    reduced_set_diagnostic: Phase8ReducedSetDiagnostic
    final_total_status: str


def load_phase8_assumptions(path: Path = ASSUMPTIONS_PATH) -> dict[str, Any]:
    return load_yaml(path)


def load_phase8_reduced_set(path: Path = REMEDIATED_REDUCED_SET_PATH) -> dict[str, Any]:
    return load_yaml(path)


def eligible_modelled_factor_ids(config: dict[str, Any] | None = None) -> tuple[str, ...]:
    cfg = config or load_phase8_assumptions()
    return tuple(cfg["modelled_factor_set"]["factor_ids"])


def eligible_modelled_factors_by_class(
    config: dict[str, Any] | None = None,
) -> dict[str, tuple[str, ...]]:
    cfg = config or load_phase8_assumptions()
    return {
        risk_class: tuple(factor_ids)
        for risk_class, factor_ids in cfg["modelled_factor_set"]["broad_risk_classes"].items()
    }


def remediated_reduced_factor_ids(config: dict[str, Any] | None = None) -> tuple[str, ...]:
    cfg = config or load_phase8_reduced_set()
    return tuple(cfg["reduced_factor_ids"])


def scaled_imcc_component(
    es_f_c: float,
    es_r_c: float,
    es_r_s: float,
) -> tuple[float, float, float]:
    if es_r_c <= 0.0:
        raise ValueError("Cannot calculate IMCC scaling ratio when ES_R_C is zero.")
    raw_ratio = es_f_c / es_r_c
    floored_ratio = max(raw_ratio, 1.0)
    return raw_ratio, floored_ratio, es_r_s * floored_ratio


def aggregate_imcc(
    unconstrained_imcc: float,
    constrained_imcc_values: list[float],
    *,
    rho: float = 0.5,
) -> float:
    return rho * unconstrained_imcc + (1.0 - rho) * sum(constrained_imcc_values)


def calculate_phase8_imcc(*, write_artifacts: bool = True) -> IMCCResult:
    assumptions = load_phase8_assumptions()
    reduced_config = load_phase8_reduced_set()
    full_factors = set(eligible_modelled_factor_ids(assumptions))
    reduced_factors = set(remediated_reduced_factor_ids(reduced_config))
    history = generate_synthetic_history()
    shocks = ten_day_shocks(history)
    current = current_period_shocks(shocks)
    windows = stress_windows_for_factor_set(
        shocks,
        reduced_factors,
        window_observations=int(assumptions["parameters"]["stress_window_observations"]),
        step_observations=int(assumptions["parameters"]["stress_window_step_observations"]),
    )
    selected = max(windows, key=lambda row: row["reduced_set_es"])
    stress_rows = [
        row
        for row in shocks
        if selected["stress_period_start"] <= row["end_date"] <= selected["stress_period_end"]
    ]
    unconstrained = imcc_component_for_factor_set(
        "UNCONSTRAINED",
        full_factors,
        reduced_factors,
        current,
        stress_rows,
        selected["stress_period_start"],
        selected["stress_period_end"],
    )
    constrained = []
    for risk_class, factors in eligible_modelled_factors_by_class(assumptions).items():
        class_full = set(factors)
        class_reduced = class_full & reduced_factors
        constrained.append(
            imcc_component_for_factor_set(
                f"CONSTRAINED_{risk_class.upper()}",
                class_full,
                class_reduced,
                current,
                stress_rows,
                selected["stress_period_start"],
                selected["stress_period_end"],
            )
        )
    rho = float(assumptions["parameters"]["imcc_rho"])
    diagnostic = phase8_reduced_set_coverage_diagnostic(shocks, full_factors, reduced_factors)
    result = IMCCResult(
        eligible_modelled_factor_ids=tuple(sorted(full_factors)),
        remediated_reduced_factor_ids=tuple(sorted(reduced_factors)),
        stress_period_start=selected["stress_period_start"],
        stress_period_end=selected["stress_period_end"],
        unconstrained=unconstrained,
        constrained_components=tuple(constrained),
        rho=rho,
        constrained_sum=sum(component.imcc_component for component in constrained),
        simulated_selected_imcc=aggregate_imcc(
            unconstrained.imcc_component,
            [component.imcc_component for component in constrained],
            rho=rho,
        ),
        reduced_set_diagnostic=diagnostic,
        final_total_status="NOT_CALCULATED",
    )
    if write_artifacts:
        write_phase8_imcc_artifacts(result)
    return result


def imcc_component_for_factor_set(
    component_id: str,
    full_factors: set[str],
    reduced_factors: set[str],
    current_rows: list[dict[str, Any]],
    stress_rows: list[dict[str, Any]],
    stress_period_start: str,
    stress_period_end: str,
) -> IMCCComponent:
    es_f_c = _lh_es(current_rows, full_factors, f"{component_id}_FULL_CURRENT")
    es_r_c = _lh_es(current_rows, reduced_factors, f"{component_id}_REDUCED_CURRENT")
    es_r_s = _lh_es(stress_rows, reduced_factors, f"{component_id}_REDUCED_STRESS")
    raw_ratio, floored_ratio, component_value = scaled_imcc_component(
        es_f_c.liquidity_adjusted_es,
        es_r_c.liquidity_adjusted_es,
        es_r_s.liquidity_adjusted_es,
    )
    return IMCCComponent(
        component_id=component_id,
        factor_ids=tuple(sorted(full_factors)),
        es_f_c=es_f_c.liquidity_adjusted_es,
        es_r_c=es_r_c.liquidity_adjusted_es,
        es_r_s=es_r_s.liquidity_adjusted_es,
        raw_scaling_ratio=raw_ratio,
        floored_scaling_ratio=floored_ratio,
        imcc_component=component_value,
        stress_period_start=stress_period_start,
        stress_period_end=stress_period_end,
    )


def stress_windows_for_factor_set(
    shocks: list[dict[str, Any]],
    reduced_factors: set[str],
    *,
    window_observations: int = 252,
    step_observations: int = 21,
) -> list[dict[str, Any]]:
    windows = []
    for start in range(0, len(shocks) - window_observations + 1, step_observations):
        window = shocks[start : start + window_observations]
        es = _lh_es(
            window,
            reduced_factors,
            f"{window[0]['end_date']}:{window[-1]['end_date']}",
        ).liquidity_adjusted_es
        windows.append(
            {
                "stress_period_start": window[0]["end_date"],
                "stress_period_end": window[-1]["end_date"],
                "observation_count": len(window),
                "reduced_set_es": es,
            }
        )
    return windows


def phase8_reduced_set_coverage_diagnostic(
    shocks: list[dict[str, Any]],
    full_factors: set[str],
    reduced_factors: set[str],
) -> Phase8ReducedSetDiagnostic:
    assumptions = load_phase8_assumptions()
    evaluation_weeks = int(assumptions["parameters"]["reduced_set_evaluation_weeks"])
    minimum = float(assumptions["parameters"]["reduced_set_minimum_average_ratio"])
    ratios = []
    for week in range(evaluation_weeks):
        end = len(shocks) - 1 - week * 5
        start = end - int(assumptions["parameters"]["stress_window_observations"]) + 1
        window = shocks[start : end + 1]
        full = _lh_es(window, full_factors, f"coverage_week_{week}_full").liquidity_adjusted_es
        reduced = _lh_es(
            window,
            reduced_factors,
            f"coverage_week_{week}_reduced",
        ).liquidity_adjusted_es
        ratios.append(reduced / full if full else 0.0)
    average = sum(ratios) / len(ratios)
    return Phase8ReducedSetDiagnostic(
        evaluation_weeks=evaluation_weeks,
        average_ratio=average,
        minimum_ratio=minimum,
        status="PASS" if average >= minimum else "REDUCED_SET_COVERAGE_FAIL",
    )


def write_phase8_imcc_artifacts(result: IMCCResult) -> None:
    MODELLED_ES_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    component_rows = []
    for component in (result.unconstrained, *result.constrained_components):
        component_rows.append(
            {
                "component_id": component.component_id,
                "factor_ids": "|".join(component.factor_ids),
                "ES_F_C": component.es_f_c,
                "ES_R_C": component.es_r_c,
                "ES_R_S": component.es_r_s,
                "raw_scaling_ratio": component.raw_scaling_ratio,
                "floored_scaling_ratio": component.floored_scaling_ratio,
                "imcc_component": component.imcc_component,
                "stress_period_start": component.stress_period_start,
                "stress_period_end": component.stress_period_end,
                "notes": "SELECTED_IMA_COMPONENT_MECHANICS",
            }
        )
    _write_csv(MODELLED_ES_ARTIFACT, component_rows)
    _write_csv(
        IMCC_ARTIFACT,
        [
            {
                "eligible_modelled_factor_ids": "|".join(result.eligible_modelled_factor_ids),
                "remediated_reduced_factor_ids": "|".join(
                    result.remediated_reduced_factor_ids
                ),
                "stress_period_start": result.stress_period_start,
                "stress_period_end": result.stress_period_end,
                "unconstrained_imcc": result.unconstrained.imcc_component,
                "constrained_sum": result.constrained_sum,
                "rho": result.rho,
                "simulated_selected_imcc": result.simulated_selected_imcc,
                "reduced_set_average_ratio": result.reduced_set_diagnostic.average_ratio,
                "reduced_set_status": result.reduced_set_diagnostic.status,
                "final_total_status": result.final_total_status,
                "notes": "Selected IMCC mechanics only; no SA capital is mixed into IMCC.",
            }
        ],
    )


def _lh_es(
    shocks: list[dict[str, Any]],
    factor_ids: set[str],
    factor_set_name: str,
) -> LiquidityHorizonESResult:
    return liquidity_horizon_expected_shortfall(
        shocks,
        factor_ids,
        factor_set_name=factor_set_name,
        observation_period=factor_set_name,
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    calculate_phase8_imcc()
