"""Deterministic equity valuation functions for selected Phase 2 instruments."""

from __future__ import annotations

import math

from frtb_lab.pricing.math import norm_cdf, norm_pdf


def equity_index_value(*, units: float, spot: float) -> float:
    return units * spot


def black_scholes_call(
    *,
    spot: float,
    strike: float,
    maturity_years: float,
    rate: float,
    dividend_yield: float,
    volatility: float,
    units: float,
) -> float:
    d1 = _d1(spot, strike, maturity_years, rate, dividend_yield, volatility)
    d2 = d1 - volatility * math.sqrt(maturity_years)
    call = spot * math.exp(-dividend_yield * maturity_years) * norm_cdf(d1)
    call -= strike * math.exp(-rate * maturity_years) * norm_cdf(d2)
    return units * call


def black_scholes_call_delta(
    *,
    spot: float,
    strike: float,
    maturity_years: float,
    rate: float,
    dividend_yield: float,
    volatility: float,
    units: float,
) -> float:
    d1 = _d1(spot, strike, maturity_years, rate, dividend_yield, volatility)
    return units * math.exp(-dividend_yield * maturity_years) * norm_cdf(d1)


def black_scholes_call_vega(
    *,
    spot: float,
    strike: float,
    maturity_years: float,
    rate: float,
    dividend_yield: float,
    volatility: float,
    units: float,
) -> float:
    d1 = _d1(spot, strike, maturity_years, rate, dividend_yield, volatility)
    return (
        units
        * spot
        * math.exp(-dividend_yield * maturity_years)
        * norm_pdf(d1)
        * math.sqrt(maturity_years)
    )


def _d1(
    spot: float,
    strike: float,
    maturity_years: float,
    rate: float,
    dividend_yield: float,
    volatility: float,
) -> float:
    numerator = math.log(spot / strike)
    numerator += (rate - dividend_yield + 0.5 * volatility * volatility) * maturity_years
    return numerator / (volatility * math.sqrt(maturity_years))
