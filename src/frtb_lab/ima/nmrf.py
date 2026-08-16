"""Selected Phase 8 MAR33.16-MAR33.17 NMRF stress-scenario mechanics."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from frtb_lab.ima.expected_shortfall import empirical_expected_shortfall
from frtb_lab.ima.liquidity_horizon import factor_liquidity_horizons
from frtb_lab.ima.synthetic_history import generate_synthetic_history, ten_day_shocks
from frtb_lab.pricing.equity import black_scholes_call
from frtb_lab.sensitivities.common import REPO_ROOT, load_market_state, load_yaml

ASSUMPTIONS_PATH = REPO_ROOT / "configs" / "ima" / "phase8_capital_demo_assumptions.yaml"
NMRF_SCENARIO_ARTIFACT = (
    REPO_ROOT / "data" / "artifacts" / "phase8_nmrf_stress_scenarios.csv"
)
SES_ARTIFACT = REPO_ROOT / "data" / "artifacts" / "phase8_ses.csv"

REMAINING_NMRF = "REMAINING_NMRF"
IDIOSYNCRATIC_CREDIT_ZERO_CORRELATION = "IDIOSYNCRATIC_CREDIT_ZERO_CORRELATION"
IDIOSYNCRATIC_EQUITY_ZERO_CORRELATION = "IDIOSYNCRATIC_EQUITY_ZERO_CORRELATION"


@dataclass(frozen=True)
class NMRFSpec:
    risk_factor_id: str
    desk_id: str
    risk_class: str
    source_liquidity_horizon: int
    shock_source_factor_id: str
    aggregation_category: str = REMAINING_NMRF
    notes: str = "Synthetic selected NMRF stress-scenario mechanics."


@dataclass(frozen=True)
class NMRFStressScenario:
    risk_factor_id: str
    desk_id: str
    risk_class: str
    source_liquidity_horizon: int
    effective_nmrf_liquidity_horizon: int
    stress_period_start: str
    stress_period_end: str
    stress_scenario_loss: float
    aggregation_category: str
    ses_contribution: float
    notes: str


@dataclass(frozen=True)
class SESResult:
    scenarios: tuple[NMRFStressScenario, ...]
    rho: float
    idiosyncratic_credit_component: float
    idiosyncratic_equity_component: float
    remaining_nmrf_component: float
    simulated_selected_ses: float
    excluded_fallback_desk_nmrf_ids: tuple[str, ...]
    final_total_status: str


def load_phase8_assumptions(path: Path = ASSUMPTIONS_PATH) -> dict[str, Any]:
    return load_yaml(path)


def canonical_nmrf_specs() -> tuple[NMRFSpec, ...]:
    horizons = factor_liquidity_horizons()
    return (
        NMRFSpec(
            risk_factor_id="RF_EQUITY_SPX_VOL_1Y",
            desk_id="TD-EQUITY",
            risk_class="equity",
            source_liquidity_horizon=horizons["RF_EQUITY_SPX_VOL_1Y"],
            shock_source_factor_id="RF_EQUITY_SPX_VOL_1Y",
            aggregation_category=REMAINING_NMRF,
            notes="Broad index volatility is not treated as idiosyncratic zero-correlation.",
        ),
    )


def effective_nmrf_liquidity_horizon(source_liquidity_horizon: int, minimum: int = 20) -> int:
    return max(int(source_liquidity_horizon), int(minimum))


def aggregate_ses(
    idiosyncratic_credit_losses: list[float],
    idiosyncratic_equity_losses: list[float],
    remaining_nmrf_losses: list[float],
    *,
    rho: float = 0.6,
) -> float:
    credit = math.sqrt(sum(value * value for value in idiosyncratic_credit_losses))
    equity = math.sqrt(sum(value * value for value in idiosyncratic_equity_losses))
    remaining_sum = sum(remaining_nmrf_losses)
    remaining_square_sum = sum(value * value for value in remaining_nmrf_losses)
    remaining = math.sqrt((rho * remaining_sum) ** 2 + (1.0 - rho * rho) * remaining_square_sum)
    return credit + equity + remaining


def calculate_phase8_ses(*, write_artifacts: bool = True) -> SESResult:
    assumptions = load_phase8_assumptions()
    specs = canonical_nmrf_specs()
    scenarios = stress_scenarios_for_specs(specs)
    rho = float(assumptions["parameters"]["ses_rho"])
    idio_credit = [
        row.ses_contribution
        for row in scenarios
        if row.aggregation_category == IDIOSYNCRATIC_CREDIT_ZERO_CORRELATION
    ]
    idio_equity = [
        row.ses_contribution
        for row in scenarios
        if row.aggregation_category == IDIOSYNCRATIC_EQUITY_ZERO_CORRELATION
    ]
    remaining = [
        row.ses_contribution for row in scenarios if row.aggregation_category == REMAINING_NMRF
    ]
    result = SESResult(
        scenarios=tuple(scenarios),
        rho=rho,
        idiosyncratic_credit_component=math.sqrt(sum(value * value for value in idio_credit)),
        idiosyncratic_equity_component=math.sqrt(sum(value * value for value in idio_equity)),
        remaining_nmrf_component=aggregate_ses([], [], remaining, rho=rho),
        simulated_selected_ses=aggregate_ses(idio_credit, idio_equity, remaining, rho=rho),
        excluded_fallback_desk_nmrf_ids=tuple(
            assumptions["eligible_nmrf_set"]["excluded_fallback_desk_nmrf_ids"]
        ),
        final_total_status="NOT_CALCULATED",
    )
    if write_artifacts:
        write_phase8_ses_artifacts(result)
    return result


def stress_scenarios_for_specs(
    specs: tuple[NMRFSpec, ...],
    *,
    window_observations: int = 252,
    step_observations: int = 21,
) -> list[NMRFStressScenario]:
    by_class: dict[str, list[NMRFSpec]] = {}
    for spec in specs:
        by_class.setdefault(spec.risk_class, []).append(spec)
    output = []
    for risk_class, risk_class_specs in by_class.items():
        common = common_stress_period_for_specs(
            tuple(risk_class_specs),
            window_observations=window_observations,
            step_observations=step_observations,
        )
        for spec in risk_class_specs:
            effective_lh = effective_nmrf_liquidity_horizon(spec.source_liquidity_horizon)
            shocks = ten_day_shocks(generate_synthetic_history(), window_days=effective_lh)
            stress_rows = [
                row
                for row in shocks
                if common["stress_period_start"] <= row["end_date"] <= common["stress_period_end"]
            ]
            loss = stress_scenario_loss(spec, stress_rows)
            output.append(
                NMRFStressScenario(
                    risk_factor_id=spec.risk_factor_id,
                    desk_id=spec.desk_id,
                    risk_class=risk_class,
                    source_liquidity_horizon=spec.source_liquidity_horizon,
                    effective_nmrf_liquidity_horizon=effective_lh,
                    stress_period_start=common["stress_period_start"],
                    stress_period_end=common["stress_period_end"],
                    stress_scenario_loss=loss,
                    aggregation_category=spec.aggregation_category,
                    ses_contribution=loss,
                    notes=spec.notes,
                )
            )
    return output


def common_stress_period_for_specs(
    specs: tuple[NMRFSpec, ...],
    *,
    window_observations: int = 252,
    step_observations: int = 21,
) -> dict[str, Any]:
    max_lh = max(effective_nmrf_liquidity_horizon(spec.source_liquidity_horizon) for spec in specs)
    shocks = ten_day_shocks(generate_synthetic_history(), window_days=max_lh)
    windows = []
    for start in range(0, len(shocks) - window_observations + 1, step_observations):
        window = shocks[start : start + window_observations]
        total_loss = sum(stress_scenario_loss(spec, window) for spec in specs)
        windows.append(
            {
                "risk_class": specs[0].risk_class,
                "stress_period_start": window[0]["end_date"],
                "stress_period_end": window[-1]["end_date"],
                "observation_count": len(window),
                "stress_scenario_loss": total_loss,
            }
        )
    if not windows:
        raise ValueError("No eligible NMRF stress windows.")
    return max(windows, key=lambda row: row["stress_scenario_loss"])


def stress_scenario_loss(spec: NMRFSpec, shocks: list[dict[str, Any]]) -> float:
    pnl = equity_vol_full_revaluation_pnl_vector(shocks, spec.shock_source_factor_id)
    return empirical_expected_shortfall(pnl, confidence_level=0.975)


def equity_vol_full_revaluation_pnl_vector(
    shocks: list[dict[str, Any]],
    shock_source_factor_id: str = "RF_EQUITY_SPX_VOL_1Y",
) -> list[float]:
    state = load_market_state()
    terms = state["instrument_terms"]["SYN_EQ_CALL"]
    equity = state["equity"]["SYN_SPX_INDEX"]
    base = black_scholes_call(
        spot=equity["spot"],
        strike=terms["strike"],
        maturity_years=terms["maturity_years"],
        rate=state["rates"]["USD"]["zero_curve"]["1Y"],
        dividend_yield=equity["dividend_yield"],
        volatility=equity["implied_volatility"]["1Y"],
        units=terms["units"],
    )
    pnl = []
    for row in shocks:
        shocked_vol = max(
            equity["implied_volatility"]["1Y"] + float(row[shock_source_factor_id]),
            0.0001,
        )
        shocked = black_scholes_call(
            spot=equity["spot"],
            strike=terms["strike"],
            maturity_years=terms["maturity_years"],
            rate=state["rates"]["USD"]["zero_curve"]["1Y"],
            dividend_yield=equity["dividend_yield"],
            volatility=shocked_vol,
            units=terms["units"],
        )
        pnl.append(shocked - base)
    return pnl


def write_phase8_ses_artifacts(result: SESResult) -> None:
    scenario_rows = [
        {
            "risk_factor_id": row.risk_factor_id,
            "desk_id": row.desk_id,
            "risk_class": row.risk_class,
            "source_liquidity_horizon": row.source_liquidity_horizon,
            "effective_nmrf_liquidity_horizon": row.effective_nmrf_liquidity_horizon,
            "stress_period_start": row.stress_period_start,
            "stress_period_end": row.stress_period_end,
            "stress_scenario_loss": row.stress_scenario_loss,
            "aggregation_category": row.aggregation_category,
            "ses_contribution": row.ses_contribution,
            "notes": row.notes,
        }
        for row in result.scenarios
    ]
    _write_csv(NMRF_SCENARIO_ARTIFACT, scenario_rows)
    _write_csv(
        SES_ARTIFACT,
        [
            {
                "rho": result.rho,
                "idiosyncratic_credit_component": result.idiosyncratic_credit_component,
                "idiosyncratic_equity_component": result.idiosyncratic_equity_component,
                "remaining_nmrf_component": result.remaining_nmrf_component,
                "simulated_selected_ses": result.simulated_selected_ses,
                "excluded_fallback_desk_nmrf_ids": "|".join(
                    result.excluded_fallback_desk_nmrf_ids
                ),
                "final_total_status": result.final_total_status,
                "notes": "SIMULATED_SELECTED_SES; no final regulatory SES claim.",
            }
        ],
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    calculate_phase8_ses()
