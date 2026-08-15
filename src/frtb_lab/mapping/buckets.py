"""Selected Phase 2 bucket mapping.

These helpers map individual risk factors to regulatory buckets. They do not
aggregate weighted sensitivities into bucket capital.
"""

from __future__ import annotations


def girr_bucket(currency: str) -> str:
    return currency


def equity_bucket(underlier: str, synthetic_assumption: str) -> str:
    if underlier != "SYN_SPX_INDEX":
        raise ValueError(f"Unsupported selected equity underlier: {underlier}")
    if synthetic_assumption != "large_market_cap_advanced_economy_index":
        raise ValueError(f"Unsupported selected equity bucket assumption: {synthetic_assumption}")
    return "EQUITY_BUCKET_12"


def fx_bucket(exchange_rate: str, reporting_currency: str) -> str:
    if reporting_currency != "USD":
        raise ValueError(
            f"Unsupported reporting currency for selected FX scope: {reporting_currency}"
        )
    if exchange_rate != "EURUSD":
        raise ValueError(f"Unsupported selected FX exchange rate: {exchange_rate}")
    return "EUR/USD"
