"""Selected-scope Standardised Approach integration for Phase 4."""

from __future__ import annotations

import csv
from pathlib import Path

from frtb_lab.sa.drc import calculate_non_securitisation_drc
from frtb_lab.sa.rrao import calculate_rrao
from frtb_lab.sa.sbm import calculate_selected_scope_sbm
from frtb_lab.sensitivities.common import REPO_ROOT

ARTIFACT_PATH = REPO_ROOT / "data" / "artifacts" / "phase4_selected_sa_capital.csv"


def calculate_selected_scope_standardised_approach(write_artifacts: bool = True) -> dict:
    sbm = calculate_selected_scope_sbm(write_artifacts=write_artifacts)
    drc = calculate_non_securitisation_drc(write_artifacts=write_artifacts)
    rrao = calculate_rrao(write_artifact=write_artifacts)
    selected_scenario = max(
        sbm["scenario_results"],
        key=lambda row: row["selected_scope_sbm_total"],
    )
    rows = [
        _row(
            "SBM",
            "delta",
            selected_scenario["gir_delta"]
            + selected_scenario["equity_delta"]
            + selected_scenario["fx_delta"],
            "BIS_MAR21",
            f"Binding scenario: {selected_scenario['scenario']}",
        ),
        _row(
            "SBM",
            "vega",
            selected_scenario["equity_vega"] + selected_scenario["fx_vega"],
            "BIS_MAR21",
            f"Binding scenario: {selected_scenario['scenario']}",
        ),
        _row(
            "SBM",
            "curvature",
            selected_scenario["equity_curvature"] + selected_scenario["fx_curvature"],
            "BIS_MAR21",
            f"Binding scenario: {selected_scenario['scenario']}",
        ),
        _row(
            "DRC",
            "non_securitisation",
            drc.total_drc,
            "BIS_MAR22",
            "Selected non-securitisation DRC only",
        ),
        _row("RRAO", "residual_risk_add_on", rrao.total_rrao, "BIS_MAR23", "Simple sum"),
    ]
    total = sum(row["capital"] for row in rows)
    rows.append(
        _row(
            "TOTAL",
            "selected_scope_standardised_approach",
            total,
            "BIS_MAR20|BIS_MAR21|BIS_MAR22|BIS_MAR23",
            "Selected-scope SA total; not complete Standardised Approach capital",
        )
    )
    output = {
        "selected_sbm": sbm["selected_scope_sbm_capital"],
        "selected_sbm_scenario": selected_scenario["scenario"],
        "non_securitisation_drc": drc.total_drc,
        "rrao": rrao.total_rrao,
        "selected_scope_standardised_approach_capital": total,
        "rows": rows,
        "drc_result": drc,
        "rrao_result": rrao,
    }
    if write_artifacts:
        write_selected_sa_artifact(rows)
    return output


def write_selected_sa_artifact(rows: list[dict], path: Path = ARTIFACT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _row(component: str, subcomponent: str, capital: float, source: str, notes: str) -> dict:
    return {
        "component": component,
        "subcomponent": subcomponent,
        "capital": capital,
        "scope_label": "selected-scope Standardised Approach",
        "source": source,
        "notes": notes,
    }


if __name__ == "__main__":
    calculate_selected_scope_standardised_approach()
