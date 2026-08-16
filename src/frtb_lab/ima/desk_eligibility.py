"""Desk-level Phase 7 IMA diagnostic aggregation."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from frtb_lab.ima.backtesting import BacktestingSummary, calculate_backtesting
from frtb_lab.ima.pla import PLAResult, calculate_pla
from frtb_lab.ima.pnl import generate_daily_pnl, load_desk_model_config
from frtb_lab.sensitivities.common import REPO_ROOT

DESK_DIAGNOSTIC_ARTIFACT = (
    REPO_ROOT / "data" / "artifacts" / "phase7_desk_diagnostic.csv"
)

IMA_TEST_GATE_PASS = "SIMULATED_IMA_TEST_GATE_PASS"
PLA_AMBER_DIAGNOSTIC = "SIMULATED_PLA_AMBER_DIAGNOSTIC"
SA_FALLBACK_REQUIRED = "SIMULATED_SA_FALLBACK_REQUIRED"
AMBER_SURCHARGE_DEFERRED = "DEFERRED_NOT_CALCULATED_PHASE7"


@dataclass(frozen=True)
class DeskDiagnostic:
    desk_id: str
    desk_name: str
    pla_zone: str
    pla_dominant_failure_metric: str
    backtesting_975_status: str
    backtesting_99_status: str
    backtesting_975_overall_exceptions: int
    backtesting_99_overall_exceptions: int
    es_candidate_factors: str
    nmrf_candidate_factors: str
    diagnostic_status: str
    pla_amber_capital_surcharge_status: str
    bank_wide_ima_approval_status: str
    notes: str


def diagnostic_status_for(
    pla_zone_value: str,
    backtesting_975_status: str,
    backtesting_99_status: str,
) -> str:
    if pla_zone_value == "RED":
        return SA_FALLBACK_REQUIRED
    if "BREACH" in {backtesting_975_status, backtesting_99_status}:
        return SA_FALLBACK_REQUIRED
    if pla_zone_value == "AMBER":
        return PLA_AMBER_DIAGNOSTIC
    if pla_zone_value == "GREEN":
        return IMA_TEST_GATE_PASS
    raise ValueError(f"Unsupported PLA zone: {pla_zone_value}")


def calculate_phase7_desk_diagnostics(
    *,
    write_artifacts: bool = True,
) -> dict[str, Any]:
    pnl_rows = generate_daily_pnl()
    pla_results = calculate_pla(pnl_rows, write_artifact=write_artifacts)
    backtesting = calculate_backtesting(pnl_rows, write_artifacts=write_artifacts)
    diagnostics = desk_diagnostics(
        pla_results,
        backtesting["summaries"],
        load_desk_model_config(),
    )
    if write_artifacts:
        write_desk_diagnostic_artifact(diagnostics)
    return {
        "status": "PHASE7_DESK_LEVEL_DIAGNOSTICS_COMPLETE",
        "pnl_rows": pnl_rows,
        "pla_results": pla_results,
        "backtesting": backtesting,
        "diagnostics": diagnostics,
    }


def desk_diagnostics(
    pla_results: list[PLAResult],
    backtesting_summaries: list[BacktestingSummary],
    config: dict[str, Any],
) -> list[DeskDiagnostic]:
    pla_by_desk = {row.desk_id: row for row in pla_results}
    bt_by_key = {
        (row.desk_id, row.confidence_level): row for row in backtesting_summaries
    }
    diagnostics = []
    for desk_id, desk in config["desk_models"].items():
        if not desk["selected_phase7_scope"]:
            continue
        pla = pla_by_desk[desk_id]
        bt_975 = bt_by_key[(desk_id, 0.975)]
        bt_99 = bt_by_key[(desk_id, 0.99)]
        status = diagnostic_status_for(
            pla.pla_zone,
            bt_975.threshold_status,
            bt_99.threshold_status,
        )
        diagnostics.append(
            DeskDiagnostic(
                desk_id=desk_id,
                desk_name=desk["desk_name"],
                pla_zone=pla.pla_zone,
                pla_dominant_failure_metric=pla.dominant_failure_metric,
                backtesting_975_status=bt_975.threshold_status,
                backtesting_99_status=bt_99.threshold_status,
                backtesting_975_overall_exceptions=bt_975.overall_exceptions,
                backtesting_99_overall_exceptions=bt_99.overall_exceptions,
                es_candidate_factors="|".join(
                    _es_candidate_factors(
                        desk["hpl_pricing_factors"],
                        desk["nmrf_candidate_factors"],
                    )
                ),
                nmrf_candidate_factors="|".join(desk["nmrf_candidate_factors"]),
                diagnostic_status=status,
                pla_amber_capital_surcharge_status=AMBER_SURCHARGE_DEFERRED,
                bank_wide_ima_approval_status="NOT_ASSESSED_PHASE7",
                notes=_diagnostic_notes(status, desk),
            )
        )
    return diagnostics


def write_desk_diagnostic_artifact(
    rows: list[DeskDiagnostic],
    path: Path = DESK_DIAGNOSTIC_ARTIFACT,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].__dict__.keys()))
        writer.writeheader()
        writer.writerows(row.__dict__ for row in rows)


def _es_candidate_factors(
    hpl_pricing_factors: list[str],
    nmrf_candidate_factors: list[str],
) -> list[str]:
    nmrf = set(nmrf_candidate_factors)
    return [factor_id for factor_id in hpl_pricing_factors if factor_id not in nmrf]


def _diagnostic_notes(status: str, desk: dict[str, Any]) -> str:
    if status == SA_FALLBACK_REQUIRED:
        return "Desk-level simulated fallback is driven by MAR32 PLA/backtesting diagnostics."
    if status == PLA_AMBER_DIAGNOSTIC:
        return "PLA amber diagnostic only; capital surcharge calculation is deferred."
    if desk["nmrf_candidate_factors"]:
        return (
            "NMRF candidate factors are reported separately and do not by themselves "
            "trigger fallback."
        )
    return "Selected desk passes Phase 7 simulated PLA/backtesting gates."


if __name__ == "__main__":
    calculate_phase7_desk_diagnostics()
