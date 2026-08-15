"""Deterministic rates valuation functions for selected Phase 2 instruments."""

from __future__ import annotations

import math


def discount_factor(rate: float, maturity_years: float) -> float:
    return math.exp(-rate * maturity_years)


def fixed_rate_bond_value(
    *,
    notional: float,
    coupon_rate: float,
    maturity_years: float,
    zero_rate: float,
    payment_frequency_per_year: int = 1,
) -> float:
    periods = int(round(maturity_years * payment_frequency_per_year))
    dt = 1.0 / payment_frequency_per_year
    coupon = notional * coupon_rate * dt
    value = 0.0
    for period in range(1, periods + 1):
        payment_time = period * dt
        cash_flow = coupon + (notional if period == periods else 0.0)
        value += cash_flow * discount_factor(zero_rate, payment_time)
    return value


def receive_fixed_irs_value(
    *,
    notional: float,
    fixed_rate: float,
    maturity_years: float,
    zero_rate: float,
    payment_frequency_per_year: int = 1,
) -> float:
    periods = int(round(maturity_years * payment_frequency_per_year))
    dt = 1.0 / payment_frequency_per_year
    annuity = sum(discount_factor(zero_rate, period * dt) * dt for period in range(1, periods + 1))
    par_rate = (1.0 - discount_factor(zero_rate, maturity_years)) / annuity
    return notional * (fixed_rate - par_rate) * annuity
