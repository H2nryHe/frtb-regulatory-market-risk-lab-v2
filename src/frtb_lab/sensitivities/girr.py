"""Selected GIRR delta/PV01 sensitivities for Phase 2."""

from __future__ import annotations

from frtb_lab.pricing.rates import fixed_rate_bond_value, receive_fixed_irs_value


def girr_pv01_sensitivity(
    *,
    instrument_id: str,
    instrument: dict,
    market_state: dict,
    bump_size: float = 0.0001,
) -> float:
    base_rate = market_state["rates"]["USD"]["zero_curve"]["5Y"]
    base_value = _value(instrument_id, instrument, base_rate)
    bumped_value = _value(instrument_id, instrument, base_rate + bump_size)
    return (bumped_value - base_value) / bump_size


def _value(instrument_id: str, instrument: dict, zero_rate: float) -> float:
    if instrument_id == "SYN_USD_GOVT_5Y":
        return fixed_rate_bond_value(
            notional=1_000_000.0,
            coupon_rate=instrument["coupon_rate"],
            maturity_years=instrument["maturity_years"],
            zero_rate=zero_rate,
            payment_frequency_per_year=instrument["payment_frequency_per_year"],
        )
    if instrument_id == "SYN_USD_IRS_5Y":
        return receive_fixed_irs_value(
            notional=2_000_000.0,
            fixed_rate=instrument["fixed_rate"],
            maturity_years=instrument["maturity_years"],
            zero_rate=zero_rate,
            payment_frequency_per_year=instrument["payment_frequency_per_year"],
        )
    raise ValueError(f"Unsupported GIRR instrument: {instrument_id}")
