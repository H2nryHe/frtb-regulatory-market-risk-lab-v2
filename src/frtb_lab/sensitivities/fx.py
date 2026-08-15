"""Selected FX delta sensitivities for Phase 2."""

from __future__ import annotations

from frtb_lab.pricing.fx import fx_forward_value, garman_kohlhagen_call


def fx_delta_sensitivity(
    *,
    instrument_id: str,
    instrument: dict,
    market_state: dict,
    relative_shock: float = 0.01,
) -> float:
    base_spot = market_state["fx"]["EURUSD"]["spot"]
    base_value = _value(instrument_id, instrument, market_state, base_spot)
    bumped_value = _value(
        instrument_id,
        instrument,
        market_state,
        base_spot * (1.0 + relative_shock),
    )
    return (bumped_value - base_value) / relative_shock


def _value(instrument_id: str, instrument: dict, market_state: dict, spot: float) -> float:
    fx_state = market_state["fx"]["EURUSD"]
    if instrument_id == "SYN_EURUSD_FWD":
        return fx_forward_value(
            spot=spot,
            strike=instrument["strike"],
            maturity_years=instrument["maturity_years"],
            domestic_rate=fx_state["domestic_rate"],
            foreign_rate=fx_state["foreign_rate"],
            foreign_notional=instrument["foreign_notional"],
            long_foreign=instrument["long_foreign"],
        )
    if instrument_id == "SYN_EURUSD_CALL":
        return garman_kohlhagen_call(
            spot=spot,
            strike=instrument["strike"],
            maturity_years=instrument["maturity_years"],
            domestic_rate=fx_state["domestic_rate"],
            foreign_rate=fx_state["foreign_rate"],
            volatility=fx_state["implied_volatility"]["1Y"],
            foreign_notional=instrument["foreign_notional"],
        )
    raise ValueError(f"Unsupported FX delta instrument: {instrument_id}")
