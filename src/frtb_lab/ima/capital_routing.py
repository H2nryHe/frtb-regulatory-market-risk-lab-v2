"""Integrated Phase 8 IMA/SA routing case-study summary."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from frtb_lab.ima.desk_eligibility import calculate_phase7_desk_diagnostics
from frtb_lab.ima.imcc import IMCCResult, calculate_phase8_imcc
from frtb_lab.ima.nmrf import SESResult, calculate_phase8_ses
from frtb_lab.sa.sbm import calculate_selected_scope_sbm
from frtb_lab.sa.standardised import calculate_selected_scope_standardised_approach
from frtb_lab.sensitivities.common import REPO_ROOT

CAPITAL_ROUTING_ARTIFACT = (
    REPO_ROOT / "data" / "artifacts" / "phase8_capital_routing.csv"
)


@dataclass(frozen=True)
class SAFallbackComponent:
    desk_id: str
    component: str
    selected_capital: float
    source: str
    completeness_status: str
    notes: str


@dataclass(frozen=True)
class IntegratedRoutingSummary:
    imcc: IMCCResult
    ses: SESResult
    sa_fallback_components: tuple[SAFallbackComponent, ...]
    final_total_status: str
    deferred_components: tuple[str, ...]


def calculate_phase8_capital_routing(*, write_artifacts: bool = True) -> IntegratedRoutingSummary:
    imcc = calculate_phase8_imcc(write_artifacts=write_artifacts)
    ses = calculate_phase8_ses(write_artifacts=write_artifacts)
    sa = calculate_selected_scope_standardised_approach(write_artifacts=False)
    fallback_components = selected_sa_fallback_components(sa)
    summary = IntegratedRoutingSummary(
        imcc=imcc,
        ses=ses,
        sa_fallback_components=tuple(fallback_components),
        final_total_status="NOT_CALCULATED",
        deferred_components=(
            "IMA_DEFAULT_RISK_MODEL",
            "MAR33_41_FINAL_60_DAY_AGGREGATION",
            "BANK_WIDE_BACKTESTING_MULTIPLIER",
            "PLA_AMBER_SURCHARGE",
            "COMPLETE_DESK_LEVEL_SA_FALLBACK_CAPITAL",
            "FINAL_BANK_WIDE_TOTAL_CAPITAL",
        ),
    )
    if write_artifacts:
        write_phase8_capital_routing_artifact(summary)
    return summary


def selected_sa_fallback_components(sa_output: dict[str, Any]) -> list[SAFallbackComponent]:
    credit_bucket = next(
        row
        for row in sa_output["drc_result"].buckets
        if row.drc_bucket == "corporates"
    )
    fx_rows = _selected_fx_sbm_components()
    return [
        *fx_rows,
        SAFallbackComponent(
            desk_id="TD-CREDIT",
            component="NON_SECURITISATION_DRC",
            selected_capital=credit_bucket.bucket_drc,
            source="BIS_MAR22",
            completeness_status="SELECTED_SA_FALLBACK_COMPONENTS",
            notes="Traceable selected non-securitisation DRC for TD-CREDIT only.",
        ),
        SAFallbackComponent(
            desk_id="ALL_SELECTED_DESKS",
            component="WHOLE_PORTFOLIO_SELECTED_SA_REFERENCE",
            selected_capital=sa_output["selected_scope_standardised_approach_capital"],
            source="BIS_MAR20|BIS_MAR21|BIS_MAR22|BIS_MAR23",
            completeness_status="REFERENCE_ONLY_NOT_ADDED_TO_IMA",
            notes="Whole selected SA reference is not added to Phase 8 IMA components.",
        ),
    ]


def write_phase8_capital_routing_artifact(summary: IntegratedRoutingSummary) -> None:
    rows = [
        {
            "branch": "SIMULATED_IMA_BRANCH",
            "component": "MODELLED_FACTOR_IMCC",
            "desk_scope": "TD-RATES|TD-EQUITY",
            "selected_amount": summary.imcc.simulated_selected_imcc,
            "scope_status": "SELECTED_IMA_COMPONENT_MECHANICS",
            "final_total_status": summary.final_total_status,
            "notes": "No SA capital mixed into IMCC.",
        },
        {
            "branch": "SIMULATED_IMA_BRANCH",
            "component": "ELIGIBLE_DESK_NMRF_SES",
            "desk_scope": "TD-EQUITY",
            "selected_amount": summary.ses.simulated_selected_ses,
            "scope_status": "SIMULATED_NMRF_STRESS_MECHANICS",
            "final_total_status": summary.final_total_status,
            "notes": "TD-FX NMRF candidate excluded because TD-FX routes to SA fallback.",
        },
    ]
    for component in summary.sa_fallback_components:
        rows.append(
            {
                "branch": "SA_FALLBACK_OR_OUT_OF_SCOPE_BRANCH",
                "component": component.component,
                "desk_scope": component.desk_id,
                "selected_amount": component.selected_capital,
                "scope_status": component.completeness_status,
                "final_total_status": summary.final_total_status,
                "notes": component.notes,
            }
        )
    _write_csv(CAPITAL_ROUTING_ARTIFACT, rows)


def _selected_fx_sbm_components() -> list[SAFallbackComponent]:
    sa = calculate_selected_scope_standardised_approach(write_artifacts=False)
    selected_sbm = calculate_selected_scope_sbm(write_artifacts=False)
    row = next(
        item
        for item in selected_sbm["scenario_results"]
        if item["scenario"] == sa["selected_sbm_scenario"]
    )
    return [
        SAFallbackComponent(
            desk_id="TD-FX",
            component="FX_DELTA",
            selected_capital=row["fx_delta"],
            source="BIS_MAR21",
            completeness_status="SELECTED_SA_FALLBACK_COMPONENTS",
            notes="Selected FX SBM delta attribution for TD-FX fallback branch.",
        ),
        SAFallbackComponent(
            desk_id="TD-FX",
            component="FX_VEGA",
            selected_capital=row["fx_vega"],
            source="BIS_MAR21",
            completeness_status="SELECTED_SA_FALLBACK_COMPONENTS",
            notes="Selected FX SBM vega attribution for TD-FX fallback branch.",
        ),
        SAFallbackComponent(
            desk_id="TD-FX",
            component="FX_CURVATURE",
            selected_capital=row["fx_curvature"],
            source="BIS_MAR21",
            completeness_status="SELECTED_SA_FALLBACK_COMPONENTS",
            notes="Selected FX SBM curvature attribution for TD-FX fallback branch.",
        ),
    ]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    calculate_phase7_desk_diagnostics(write_artifacts=True)
    calculate_phase8_capital_routing()
