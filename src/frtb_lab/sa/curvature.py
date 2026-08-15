"""Selected full-revaluation curvature implementation for Phase 3."""

from __future__ import annotations

import math
from collections import defaultdict

from frtb_lab.pricing.equity import black_scholes_call
from frtb_lab.pricing.fx import garman_kohlhagen_call
from frtb_lab.sa.correlations import Scenario, curvature_correlation, selected_gamma, selected_rho
from frtb_lab.sensitivities.common import load_market_state
from frtb_lab.sensitivities.equity import equity_spot_delta_sensitivity
from frtb_lab.sensitivities.fx import fx_delta_sensitivity


def selected_curvature_records(market_state: dict | None = None) -> list[dict]:
    state = market_state or load_market_state()
    return [
        _equity_call_curvature(state),
        _fx_call_curvature(state),
    ]


def curvature_capital(records: list[dict], scenario: Scenario) -> dict:
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_bucket[record["bucket"]].append(record)
    bucket_results = []
    for bucket, bucket_records in sorted(by_bucket.items()):
        up = _bucket_direction_capital(bucket_records, scenario, "cvr_up")
        down = _bucket_direction_capital(bucket_records, scenario, "cvr_down")
        selected_direction = "up" if up >= down else "down"
        bucket_results.append(
            {
                "bucket": bucket,
                "k_b": max(up, down),
                "up_k_b": up,
                "down_k_b": down,
                "selected_direction": selected_direction,
            }
        )
    risk_class = records[0]["risk_class"] if records else ""
    total = _across_bucket_curvature(bucket_results, risk_class, scenario)
    return {
        "risk_class": risk_class,
        "sensitivity_type": "curvature",
        "scenario": scenario,
        "records": records,
        "bucket_results": bucket_results,
        "risk_class_capital": total,
    }


def _bucket_direction_capital(records: list[dict], scenario: Scenario, field: str) -> float:
    radicand = 0.0
    for left in records:
        for right in records:
            rho = curvature_correlation(_medium_delta_rho(left, right), scenario)
            left_loss = max(float(left[field]), 0.0)
            right_loss = max(float(right[field]), 0.0)
            radicand += rho * left_loss * right_loss
    return math.sqrt(max(radicand, 0.0))


def _across_bucket_curvature(
    bucket_results: list[dict],
    risk_class: str,
    scenario: Scenario,
) -> float:
    radicand = sum(bucket["k_b"] ** 2 for bucket in bucket_results)
    for left in bucket_results:
        for right in bucket_results:
            if left["bucket"] == right["bucket"]:
                continue
            gamma = curvature_correlation(
                selected_gamma(left["bucket"], right["bucket"], risk_class, "MEDIUM"),
                scenario,
            )
            radicand += gamma * left["k_b"] * right["k_b"]
    return math.sqrt(max(radicand, 0.0))


def _medium_delta_rho(record_a: dict, record_b: dict) -> float:
    if record_a["risk_factor_id"] == record_b["risk_factor_id"]:
        return 1.0
    return selected_rho(
        {**record_a, "sensitivity_type": "delta"},
        {**record_b, "sensitivity_type": "delta"},
        "MEDIUM",
    )


def _equity_call_curvature(state: dict) -> dict:
    instrument = state["instrument_terms"]["SYN_EQ_CALL"]
    equity = state["equity"]["SYN_SPX_INDEX"]
    spot = equity["spot"]
    shock = 0.15
    base = _equity_call_value(state, spot)
    up = _equity_call_value(state, spot * (1.0 + shock))
    down = _equity_call_value(state, spot * (1.0 - shock))
    delta = equity_spot_delta_sensitivity(
        instrument_id="SYN_EQ_CALL",
        instrument=instrument,
        market_state=state,
    )
    return {
        "instrument_id": "SYN_EQ_CALL",
        "risk_class": "EQUITY",
        "risk_factor_id": "RF_EQUITY_SPX_SPOT",
        "bucket": "EQUITY_BUCKET_12",
        "shock": shock,
        "base_value": base,
        "up_value": up,
        "down_value": down,
        "delta_sensitivity": delta,
        "cvr_up": -(up - base - delta * shock),
        "cvr_down": -(down - base + delta * shock),
    }


def _fx_call_curvature(state: dict) -> dict:
    instrument = state["instrument_terms"]["SYN_EURUSD_CALL"]
    fx = state["fx"]["EURUSD"]
    spot = fx["spot"]
    shock = 0.15
    base = _fx_call_value(state, spot)
    up = _fx_call_value(state, spot * (1.0 + shock))
    down = _fx_call_value(state, spot * (1.0 - shock))
    delta = fx_delta_sensitivity(
        instrument_id="SYN_EURUSD_CALL",
        instrument=instrument,
        market_state=state,
    )
    return {
        "instrument_id": "SYN_EURUSD_CALL",
        "risk_class": "FX",
        "risk_factor_id": "RF_FX_EURUSD_SPOT",
        "bucket": "EUR/USD",
        "shock": shock,
        "base_value": base,
        "up_value": up,
        "down_value": down,
        "delta_sensitivity": delta,
        "cvr_up": -(up - base - delta * shock),
        "cvr_down": -(down - base + delta * shock),
    }


def _equity_call_value(state: dict, spot: float) -> float:
    instrument = state["instrument_terms"]["SYN_EQ_CALL"]
    equity = state["equity"]["SYN_SPX_INDEX"]
    return black_scholes_call(
        spot=spot,
        strike=instrument["strike"],
        maturity_years=instrument["maturity_years"],
        rate=state["rates"]["USD"]["zero_curve"]["1Y"],
        dividend_yield=equity["dividend_yield"],
        volatility=equity["implied_volatility"]["1Y"],
        units=instrument["units"],
    )


def _fx_call_value(state: dict, spot: float) -> float:
    instrument = state["instrument_terms"]["SYN_EURUSD_CALL"]
    fx = state["fx"]["EURUSD"]
    return garman_kohlhagen_call(
        spot=spot,
        strike=instrument["strike"],
        maturity_years=instrument["maturity_years"],
        domestic_rate=fx["domestic_rate"],
        foreign_rate=fx["foreign_rate"],
        volatility=fx["implied_volatility"]["1Y"],
        foreign_notional=instrument["foreign_notional"],
    )
