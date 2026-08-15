"""Selected equity delta sensitivities for Phase 2."""

from __future__ import annotations

from frtb_lab.pricing.equity import black_scholes_call, equity_index_value


def equity_spot_delta_sensitivity(
    *,
    instrument_id: str,
    instrument: dict,
    market_state: dict,
    relative_shock: float = 0.01,
) -> float:
    base_spot = market_state["equity"]["SYN_SPX_INDEX"]["spot"]
    base_value = _value(instrument_id, instrument, market_state, base_spot)
    bumped_value = _value(
        instrument_id,
        instrument,
        market_state,
        base_spot * (1.0 + relative_shock),
    )
    return (bumped_value - base_value) / relative_shock


def _value(instrument_id: str, instrument: dict, market_state: dict, spot: float) -> float:
    equity_state = market_state["equity"]["SYN_SPX_INDEX"]
    usd_rate = market_state["rates"]["USD"]["zero_curve"]["1Y"]
    if instrument_id == "SYN_EQ_INDEX":
        return equity_index_value(units=instrument["units"], spot=spot)
    if instrument_id == "SYN_EQ_CALL":
        return black_scholes_call(
            spot=spot,
            strike=instrument["strike"],
            maturity_years=instrument["maturity_years"],
            rate=usd_rate,
            dividend_yield=equity_state["dividend_yield"],
            volatility=equity_state["implied_volatility"]["1Y"],
            units=instrument["units"],
        )
    raise ValueError(f"Unsupported equity delta instrument: {instrument_id}")
