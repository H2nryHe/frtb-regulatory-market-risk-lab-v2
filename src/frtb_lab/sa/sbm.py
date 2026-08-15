"""Selected-scope SBM orchestration for Phase 3."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from frtb_lab.sa.aggregation import net_sensitivities, risk_class_capital
from frtb_lab.sa.correlations import Scenario
from frtb_lab.sa.curvature import curvature_capital, selected_curvature_records
from frtb_lab.sensitivities.common import REPO_ROOT
from frtb_lab.sensitivities.generate import generate_phase2_sensitivities

SCENARIOS: tuple[Scenario, ...] = ("LOW", "MEDIUM", "HIGH")
ARTIFACTS = {
    "delta": REPO_ROOT / "data" / "artifacts" / "phase3_delta_capital.csv",
    "vega": REPO_ROOT / "data" / "artifacts" / "phase3_vega_capital.csv",
    "curvature": REPO_ROOT / "data" / "artifacts" / "phase3_curvature.csv",
    "scenarios": REPO_ROOT / "data" / "artifacts" / "phase3_sbm_scenarios.csv",
}


def calculate_selected_scope_sbm(write_artifacts: bool = True) -> dict:
    phase2_rows = generate_phase2_sensitivities()
    sensitivity_records = [_record_from_phase2(row) for row in phase2_rows]
    curvature_records = selected_curvature_records()
    scenario_results = []
    component_rows = {"delta": [], "vega": [], "curvature": []}
    for scenario in SCENARIOS:
        component_capitals = _component_capitals(sensitivity_records, curvature_records, scenario)
        scenario_total = sum(result["risk_class_capital"] for result in component_capitals)
        scenario_results.append(
            {
                "scenario": scenario,
                "gir_delta": _capital(component_capitals, "GIRR", "delta"),
                "equity_delta": _capital(component_capitals, "EQUITY", "delta"),
                "fx_delta": _capital(component_capitals, "FX", "delta"),
                "equity_vega": _capital(component_capitals, "EQUITY", "vega"),
                "fx_vega": _capital(component_capitals, "FX", "vega"),
                "equity_curvature": _capital(component_capitals, "EQUITY", "curvature"),
                "fx_curvature": _capital(component_capitals, "FX", "curvature"),
                "selected_scope_sbm_total": scenario_total,
            }
        )
        for result in component_capitals:
            component_rows[result["sensitivity_type"]].extend(_artifact_rows(result))
    selected = max(scenario_results, key=lambda row: row["selected_scope_sbm_total"])
    output = {
        "scenario_results": scenario_results,
        "selected_scope_sbm_capital": selected["selected_scope_sbm_total"],
        "selected_scenario": selected["scenario"],
        "component_rows": component_rows,
    }
    if write_artifacts:
        _write_artifacts(output)
    return output


def _component_capitals(
    sensitivity_records: list[dict],
    curvature_records: list[dict],
    scenario: Scenario,
) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for record in sensitivity_records:
        grouped[(record["risk_class"], record["sensitivity_type"])].append(record)
    results = []
    for (_risk_class, _sensitivity_type), records in sorted(grouped.items()):
        results.append(risk_class_capital(net_sensitivities(records), scenario))
    for risk_class in ["EQUITY", "FX"]:
        records = [record for record in curvature_records if record["risk_class"] == risk_class]
        results.append(curvature_capital(records, scenario))
    return results


def _record_from_phase2(row: dict) -> dict:
    tenor = row["regulatory_tenor"]
    option_maturity = 1.0 if tenor == "1Y" else ""
    return {
        "instrument_id": row["instrument_id"],
        "risk_class": row["risk_class"],
        "risk_factor_id": row["risk_factor_id"],
        "risk_factor_type": row["risk_factor_type"],
        "sensitivity_type": row["sensitivity_type"],
        "bucket": row["regulatory_bucket"],
        "tenor": tenor,
        "tenor_years": 5.0 if tenor == "5Y" else "",
        "option_maturity": option_maturity,
        "raw_sensitivity": float(row["raw_sensitivity"]),
        "risk_weight": float(row["risk_weight"]),
        "weighted_sensitivity": float(row["weighted_sensitivity"]),
    }


def _capital(results: list[dict], risk_class: str, sensitivity_type: str) -> float:
    for result in results:
        if result["risk_class"] == risk_class and result["sensitivity_type"] == sensitivity_type:
            return result["risk_class_capital"]
    return 0.0


def _artifact_rows(result: dict) -> list[dict]:
    rows = []
    for bucket in result["bucket_results"]:
        rows.append(
            {
                "scenario": result["scenario"],
                "risk_class": result["risk_class"],
                "sensitivity_type": result["sensitivity_type"],
                "bucket": bucket["bucket"],
                "k_b": bucket["k_b"],
                "s_b": bucket.get("s_b", ""),
                "risk_class_capital": result["risk_class_capital"],
                "alternative_used": result.get("alternative_used", False),
            }
        )
    return rows


def _write_artifacts(output: dict) -> None:
    for path in ARTIFACTS.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(ARTIFACTS["scenarios"], output["scenario_results"])
    _write_csv(ARTIFACTS["delta"], output["component_rows"]["delta"])
    _write_csv(ARTIFACTS["vega"], output["component_rows"]["vega"])
    _write_csv(ARTIFACTS["curvature"], output["component_rows"]["curvature"])


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    calculate_selected_scope_sbm()
