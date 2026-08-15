"""Selected option-level regulatory vega sensitivities for Phase 2."""

from __future__ import annotations

from bisect import bisect_left

from frtb_lab.pricing.equity import black_scholes_call_vega
from frtb_lab.pricing.fx import garman_kohlhagen_call_vega


def regulatory_vega_sensitivity(*, model_vega: float, implied_volatility: float) -> float:
    return model_vega * implied_volatility


def equity_option_model_vega(*, instrument: dict, market_state: dict) -> float:
    equity_state = market_state["equity"]["SYN_SPX_INDEX"]
    return black_scholes_call_vega(
        spot=equity_state["spot"],
        strike=instrument["strike"],
        maturity_years=instrument["maturity_years"],
        rate=market_state["rates"]["USD"]["zero_curve"]["1Y"],
        dividend_yield=equity_state["dividend_yield"],
        volatility=equity_state["implied_volatility"]["1Y"],
        units=instrument["units"],
    )


def fx_option_model_vega(*, instrument: dict, market_state: dict) -> float:
    fx_state = market_state["fx"]["EURUSD"]
    return garman_kohlhagen_call_vega(
        spot=fx_state["spot"],
        strike=instrument["strike"],
        maturity_years=instrument["maturity_years"],
        domestic_rate=fx_state["domestic_rate"],
        foreign_rate=fx_state["foreign_rate"],
        volatility=fx_state["implied_volatility"]["1Y"],
        foreign_notional=instrument["foreign_notional"],
    )


def maturity_allocation(
    maturity_years: float,
    prescribed_tenors: list[float],
) -> dict[float, float]:
    tenors = sorted(prescribed_tenors)
    if maturity_years in tenors:
        return {maturity_years: 1.0}
    index = bisect_left(tenors, maturity_years)
    if index == 0 or index == len(tenors):
        raise ValueError(f"Maturity {maturity_years} is outside prescribed tenor range.")
    lower = tenors[index - 1]
    upper = tenors[index]
    upper_weight = (maturity_years - lower) / (upper - lower)
    return {lower: 1.0 - upper_weight, upper: upper_weight}
