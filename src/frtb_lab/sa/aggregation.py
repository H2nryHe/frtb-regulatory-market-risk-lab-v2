"""Delta and vega netting and aggregation for selected Phase 3 SBM scope."""

from __future__ import annotations

import math
from collections import defaultdict

from frtb_lab.sa.correlations import Scenario, selected_gamma, selected_rho


def net_sensitivities(records: list[dict]) -> list[dict]:
    grouped: dict[tuple, dict] = {}
    for record in records:
        key = (
            record["risk_class"],
            record["sensitivity_type"],
            record["bucket"],
            record["risk_factor_id"],
            record.get("tenor", ""),
            record.get("option_maturity", ""),
        )
        if key not in grouped:
            grouped[key] = {**record, "raw_sensitivity": 0.0}
        grouped[key]["raw_sensitivity"] += float(record["raw_sensitivity"])
    netted = []
    for record in grouped.values():
        record["weighted_sensitivity"] = float(record["raw_sensitivity"]) * float(
            record["risk_weight"]
        )
        netted.append(record)
    return netted


def bucket_capital(records: list[dict], scenario: Scenario) -> dict:
    if not records:
        return {"bucket": "", "k_b": 0.0, "s_b": 0.0, "radicand": 0.0}
    radicand = 0.0
    for left in records:
        for right in records:
            rho = selected_rho(left, right, scenario)
            radicand += rho * left["weighted_sensitivity"] * right["weighted_sensitivity"]
    floored = max(radicand, 0.0)
    k_b = math.sqrt(floored)
    return {
        "bucket": records[0]["bucket"],
        "k_b": k_b,
        "s_b": sum(record["weighted_sensitivity"] for record in records),
        "radicand": radicand,
    }


def risk_class_capital(netted_records: list[dict], scenario: Scenario) -> dict:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for record in netted_records:
        buckets[record["bucket"]].append(record)
    bucket_results = {
        bucket: bucket_capital(records, scenario) for bucket, records in sorted(buckets.items())
    }
    risk_class = netted_records[0]["risk_class"] if netted_records else ""
    capital, radicand, alternative_used = _across_bucket_capital(
        bucket_results,
        risk_class,
        scenario,
        use_alternative=False,
    )
    if radicand < 0.0:
        capital, radicand, alternative_used = _across_bucket_capital(
            bucket_results,
            risk_class,
            scenario,
            use_alternative=True,
        )
    return {
        "risk_class": risk_class,
        "sensitivity_type": netted_records[0]["sensitivity_type"] if netted_records else "",
        "scenario": scenario,
        "bucket_results": list(bucket_results.values()),
        "netted_records": netted_records,
        "risk_class_capital": capital,
        "across_bucket_radicand": radicand,
        "alternative_used": alternative_used,
    }


def _across_bucket_capital(
    bucket_results: dict[str, dict],
    risk_class: str,
    scenario: Scenario,
    *,
    use_alternative: bool,
) -> tuple[float, float, bool]:
    radicand = sum(bucket["k_b"] ** 2 for bucket in bucket_results.values())
    for bucket_a, result_a in bucket_results.items():
        for bucket_b, result_b in bucket_results.items():
            if bucket_a == bucket_b:
                continue
            s_a = _alternative_s(result_a) if use_alternative else result_a["s_b"]
            s_b = _alternative_s(result_b) if use_alternative else result_b["s_b"]
            radicand += selected_gamma(bucket_a, bucket_b, risk_class, scenario) * s_a * s_b
    return math.sqrt(max(radicand, 0.0)), radicand, use_alternative


def _alternative_s(bucket_result: dict) -> float:
    return max(min(bucket_result["s_b"], bucket_result["k_b"]), -bucket_result["k_b"])
