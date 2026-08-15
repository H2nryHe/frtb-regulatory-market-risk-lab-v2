"""Selected MAR21 correlation parameters and scenario transformations."""

from __future__ import annotations

import math
from typing import Literal

Scenario = Literal["LOW", "MEDIUM", "HIGH"]


def scenario_correlation(correlation: float, scenario: Scenario) -> float:
    if scenario == "MEDIUM":
        return correlation
    if scenario == "HIGH":
        return min(1.25 * correlation, 1.0)
    if scenario == "LOW":
        return max(2.0 * correlation - 1.0, 0.75 * correlation)
    raise ValueError(f"Unsupported scenario: {scenario}")


def curvature_correlation(correlation: float, scenario: Scenario) -> float:
    return scenario_correlation(correlation * correlation, scenario)


def girr_delta_rho(
    tenor_a: float,
    tenor_b: float,
    *,
    same_curve: bool = True,
    scenario: Scenario = "MEDIUM",
) -> float:
    if tenor_a == tenor_b:
        base = 1.0 if same_curve else 0.999
    else:
        base = _girr_same_curve_base(tenor_a, tenor_b)
        if not same_curve:
            base *= 0.999
    return scenario_correlation(base, scenario)


def girr_cross_bucket_gamma(scenario: Scenario = "MEDIUM") -> float:
    return scenario_correlation(0.50, scenario)


def equity_delta_rho(bucket: str, scenario: Scenario = "MEDIUM") -> float:
    if bucket in {"EQUITY_BUCKET_12", "EQUITY_BUCKET_13"}:
        return scenario_correlation(0.80, scenario)
    raise ValueError(f"Unsupported selected equity bucket: {bucket}")


def equity_cross_bucket_gamma(bucket_a: str, bucket_b: str, scenario: Scenario = "MEDIUM") -> float:
    pair = {bucket_a, bucket_b}
    if pair == {"EQUITY_BUCKET_12", "EQUITY_BUCKET_13"}:
        return scenario_correlation(0.75, scenario)
    return scenario_correlation(0.45, scenario)


def fx_cross_bucket_gamma(scenario: Scenario = "MEDIUM") -> float:
    return scenario_correlation(0.60, scenario)


def vega_maturity_correlation(
    maturity_a: float,
    maturity_b: float,
    *,
    alpha: float = 0.01,
    scenario: Scenario = "MEDIUM",
) -> float:
    base = math.exp(-alpha * abs(maturity_a - maturity_b) / min(maturity_a, maturity_b))
    return scenario_correlation(base, scenario)


def selected_rho(record_a: dict, record_b: dict, scenario: Scenario) -> float:
    if record_a["risk_factor_id"] == record_b["risk_factor_id"]:
        return 1.0
    risk_class = record_a["risk_class"]
    if risk_class != record_b["risk_class"]:
        raise ValueError("Cannot calculate rho across risk classes.")
    if record_a["sensitivity_type"] == "vega":
        delta_component = _delta_component_for_vega(record_a, record_b, scenario)
        maturity_component = vega_maturity_correlation(
            float(record_a.get("option_maturity", 1.0)),
            float(record_b.get("option_maturity", 1.0)),
            scenario=scenario,
        )
        return delta_component * maturity_component
    if risk_class == "GIRR":
        return girr_delta_rho(
            float(record_a.get("tenor_years", 5.0)),
            float(record_b.get("tenor_years", 5.0)),
            same_curve=record_a.get("curve", "OIS") == record_b.get("curve", "OIS"),
            scenario=scenario,
        )
    if risk_class == "EQUITY":
        return equity_delta_rho(record_a["bucket"], scenario)
    if risk_class == "FX":
        return 1.0 if record_a["bucket"] == record_b["bucket"] else fx_cross_bucket_gamma(scenario)
    raise ValueError(f"Unsupported selected risk class: {risk_class}")


def selected_gamma(bucket_a: str, bucket_b: str, risk_class: str, scenario: Scenario) -> float:
    if bucket_a == bucket_b:
        return 1.0
    if risk_class == "GIRR":
        return girr_cross_bucket_gamma(scenario)
    if risk_class == "EQUITY":
        return equity_cross_bucket_gamma(bucket_a, bucket_b, scenario)
    if risk_class == "FX":
        return fx_cross_bucket_gamma(scenario)
    raise ValueError(f"Unsupported selected risk class: {risk_class}")


def _delta_component_for_vega(record_a: dict, record_b: dict, scenario: Scenario) -> float:
    risk_class = record_a["risk_class"]
    if risk_class == "EQUITY":
        return equity_delta_rho(record_a["bucket"], scenario)
    if risk_class == "FX":
        return 1.0 if record_a["bucket"] == record_b["bucket"] else fx_cross_bucket_gamma(scenario)
    if risk_class == "GIRR":
        return girr_delta_rho(
            float(record_a.get("underlying_maturity", 5.0)),
            float(record_b.get("underlying_maturity", 5.0)),
            scenario=scenario,
        )
    raise ValueError(f"Unsupported selected vega risk class: {risk_class}")


def _girr_same_curve_base(tenor_a: float, tenor_b: float) -> float:
    selected = {
        (1.0, 5.0): 0.887,
        (5.0, 10.0): 0.970,
    }
    key = tuple(sorted((tenor_a, tenor_b)))
    if key in selected:
        return selected[key]
    theta = 0.03
    return max(math.exp(-theta * abs(tenor_a - tenor_b) / min(tenor_a, tenor_b)), 0.40)
