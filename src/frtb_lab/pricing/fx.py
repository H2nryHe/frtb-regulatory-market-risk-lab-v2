"""Deterministic FX valuation functions for selected Phase 2 instruments."""

from __future__ import annotations

import math

from frtb_lab.pricing.math import norm_cdf, norm_pdf


def fx_forward_value(
    *,
    spot: float,
    strike: float,
    maturity_years: float,
    domestic_rate: float,
    foreign_rate: float,
    foreign_notional: float,
    long_foreign: bool = True,
) -> float:
    value = foreign_notional * (
        spot * math.exp(-foreign_rate * maturity_years)
        - strike * math.exp(-domestic_rate * maturity_years)
    )
    return value if long_foreign else -value


def garman_kohlhagen_call(
    *,
    spot: float,
    strike: float,
    maturity_years: float,
    domestic_rate: float,
    foreign_rate: float,
    volatility: float,
    foreign_notional: float,
) -> float:
    d1 = _d1(spot, strike, maturity_years, domestic_rate, foreign_rate, volatility)
    d2 = d1 - volatility * math.sqrt(maturity_years)
    call = spot * math.exp(-foreign_rate * maturity_years) * norm_cdf(d1)
    call -= strike * math.exp(-domestic_rate * maturity_years) * norm_cdf(d2)
    return foreign_notional * call


def garman_kohlhagen_call_delta(
    *,
    spot: float,
    strike: float,
    maturity_years: float,
    domestic_rate: float,
    foreign_rate: float,
    volatility: float,
    foreign_notional: float,
) -> float:
    d1 = _d1(spot, strike, maturity_years, domestic_rate, foreign_rate, volatility)
    return foreign_notional * math.exp(-foreign_rate * maturity_years) * norm_cdf(d1)


def garman_kohlhagen_call_vega(
    *,
    spot: float,
    strike: float,
    maturity_years: float,
    domestic_rate: float,
    foreign_rate: float,
    volatility: float,
    foreign_notional: float,
) -> float:
    d1 = _d1(spot, strike, maturity_years, domestic_rate, foreign_rate, volatility)
    return (
        foreign_notional
        * spot
        * math.exp(-foreign_rate * maturity_years)
        * norm_pdf(d1)
        * math.sqrt(maturity_years)
    )


def _d1(
    spot: float,
    strike: float,
    maturity_years: float,
    domestic_rate: float,
    foreign_rate: float,
    volatility: float,
) -> float:
    numerator = math.log(spot / strike)
    numerator += (domestic_rate - foreign_rate + 0.5 * volatility * volatility) * maturity_years
    return numerator / (volatility * math.sqrt(maturity_years))
