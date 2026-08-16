"""Current-position revaluation under synthetic 10-day shocks."""

from __future__ import annotations

import math
from typing import Any

from frtb_lab.pricing.equity import black_scholes_call, equity_index_value
from frtb_lab.pricing.fx import fx_forward_value, garman_kohlhagen_call
from frtb_lab.pricing.rates import fixed_rate_bond_value, receive_fixed_irs_value
from frtb_lab.sensitivities.common import load_market_state

FULL_FACTOR_IDS = (
    "RF_GIRR_USD_5Y_RATE",
    "RF_EQUITY_SPX_SPOT",
    "RF_EQUITY_SPX_VOL_1Y",
    "RF_FX_EURUSD_SPOT",
    "RF_FX_EURUSD_VOL_1Y",
)


def portfolio_pnl_for_shock(
    shock: dict[str, Any],
    factor_ids: set[str] | list[str] | tuple[str, ...] = FULL_FACTOR_IDS,
) -> float:
    state = load_market_state()
    selected = set(factor_ids)
    base = _portfolio_value(state)
    shocked = _portfolio_value(_shocked_state(state, shock, selected))
    return shocked - base


def portfolio_pnl_vector(shocks: list[dict[str, Any]], factor_ids: set[str]) -> list[float]:
    state = load_market_state()
    selected = set(factor_ids)
    base = _portfolio_value(state)
    return [_portfolio_value(_shocked_state(state, row, selected)) - base for row in shocks]


def _portfolio_value(state: dict[str, Any]) -> float:
    terms = state["instrument_terms"]
    usd_5y = state["rates"]["USD"]["zero_curve"]["5Y"]
    equity = state["equity"]["SYN_SPX_INDEX"]
    fx = state["fx"]["EURUSD"]
    value = fixed_rate_bond_value(
        notional=1_000_000.0,
        coupon_rate=terms["SYN_USD_GOVT_5Y"]["coupon_rate"],
        maturity_years=terms["SYN_USD_GOVT_5Y"]["maturity_years"],
        zero_rate=usd_5y,
        payment_frequency_per_year=terms["SYN_USD_GOVT_5Y"]["payment_frequency_per_year"],
    )
    value += receive_fixed_irs_value(
        notional=2_000_000.0,
        fixed_rate=terms["SYN_USD_IRS_5Y"]["fixed_rate"],
        maturity_years=terms["SYN_USD_IRS_5Y"]["maturity_years"],
        zero_rate=usd_5y,
        payment_frequency_per_year=terms["SYN_USD_IRS_5Y"]["payment_frequency_per_year"],
    )
    value += equity_index_value(units=terms["SYN_EQ_INDEX"]["units"], spot=equity["spot"])
    value += black_scholes_call(
        spot=equity["spot"],
        strike=terms["SYN_EQ_CALL"]["strike"],
        maturity_years=terms["SYN_EQ_CALL"]["maturity_years"],
        rate=state["rates"]["USD"]["zero_curve"]["1Y"],
        dividend_yield=equity["dividend_yield"],
        volatility=equity["implied_volatility"]["1Y"],
        units=terms["SYN_EQ_CALL"]["units"],
    )
    value += fx_forward_value(
        spot=fx["spot"],
        strike=terms["SYN_EURUSD_FWD"]["strike"],
        maturity_years=terms["SYN_EURUSD_FWD"]["maturity_years"],
        domestic_rate=fx["domestic_rate"],
        foreign_rate=fx["foreign_rate"],
        foreign_notional=terms["SYN_EURUSD_FWD"]["foreign_notional"],
        long_foreign=terms["SYN_EURUSD_FWD"]["long_foreign"],
    )
    value += garman_kohlhagen_call(
        spot=fx["spot"],
        strike=terms["SYN_EURUSD_CALL"]["strike"],
        maturity_years=terms["SYN_EURUSD_CALL"]["maturity_years"],
        domestic_rate=fx["domestic_rate"],
        foreign_rate=fx["foreign_rate"],
        volatility=fx["implied_volatility"]["1Y"],
        foreign_notional=terms["SYN_EURUSD_CALL"]["foreign_notional"],
    )
    return value


def _shocked_state(
    state: dict[str, Any],
    shock: dict[str, Any],
    factor_ids: set[str],
) -> dict[str, Any]:
    shocked = {
        **state,
        "rates": {
            currency: {**data, "zero_curve": dict(data["zero_curve"])}
            for currency, data in state["rates"].items()
        },
        "equity": {
            key: {**value, "implied_volatility": dict(value["implied_volatility"])}
            for key, value in state["equity"].items()
        },
        "fx": {
            key: {**value, "implied_volatility": dict(value["implied_volatility"])}
            for key, value in state["fx"].items()
        },
    }
    if "RF_GIRR_USD_5Y_RATE" in factor_ids:
        shocked["rates"]["USD"]["zero_curve"]["5Y"] += float(shock["RF_GIRR_USD_5Y_RATE"])
    if "RF_EQUITY_SPX_SPOT" in factor_ids:
        shocked["equity"]["SYN_SPX_INDEX"]["spot"] *= math.exp(float(shock["RF_EQUITY_SPX_SPOT"]))
    if "RF_EQUITY_SPX_VOL_1Y" in factor_ids:
        shocked["equity"]["SYN_SPX_INDEX"]["implied_volatility"]["1Y"] = max(
            shocked["equity"]["SYN_SPX_INDEX"]["implied_volatility"]["1Y"]
            + float(shock["RF_EQUITY_SPX_VOL_1Y"]),
            0.0001,
        )
    if "RF_FX_EURUSD_SPOT" in factor_ids:
        shocked["fx"]["EURUSD"]["spot"] *= math.exp(float(shock["RF_FX_EURUSD_SPOT"]))
    if "RF_FX_EURUSD_VOL_1Y" in factor_ids:
        shocked["fx"]["EURUSD"]["implied_volatility"]["1Y"] = max(
            shocked["fx"]["EURUSD"]["implied_volatility"]["1Y"]
            + float(shock["RF_FX_EURUSD_VOL_1Y"]),
            0.0001,
        )
    return shocked
