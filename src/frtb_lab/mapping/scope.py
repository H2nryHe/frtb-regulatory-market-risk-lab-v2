"""Project-level trading-book scope validation for Phase 1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from frtb_lab.instruments.base import Instrument

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_PORTFOLIO_PATH = REPO_ROOT / "data" / "fixtures" / "canonical_portfolio.yaml"

SUPPORTED_RISK_CLASSES = frozenset({"GIRR", "EQUITY", "FX", "CREDIT"})
SUPPORTED_INSTRUMENT_RISK_CLASS = {
    "GOVERNMENT_BOND": "GIRR",
    "INTEREST_RATE_SWAP": "GIRR",
    "EQUITY_INDEX": "EQUITY",
    "EQUITY_OPTION": "EQUITY",
    "EQUITY_BARRIER_OPTION": "EQUITY",
    "FX_FORWARD": "FX",
    "FX_OPTION": "FX",
    "CORPORATE_BOND": "CREDIT",
}
OPTION_INSTRUMENT_TYPES = frozenset({"EQUITY_OPTION", "EQUITY_BARRIER_OPTION", "FX_OPTION"})
EXOTIC_INSTRUMENT_TYPES = frozenset({"EQUITY_BARRIER_OPTION"})
DRC_RELEVANT_INSTRUMENT_TYPES = frozenset({"CORPORATE_BOND"})
MATURITY_REQUIRED_INSTRUMENT_TYPES = frozenset(
    {
        "GOVERNMENT_BOND",
        "INTEREST_RATE_SWAP",
        "EQUITY_OPTION",
        "EQUITY_BARRIER_OPTION",
        "FX_FORWARD",
        "FX_OPTION",
        "CORPORATE_BOND",
    }
)


class PortfolioValidationError(ValueError):
    """Raised when the selected synthetic portfolio violates Phase 1 rules."""


def load_canonical_portfolio(path: Path = CANONICAL_PORTFOLIO_PATH) -> dict[str, Any]:
    with path.open() as handle:
        data = yaml.safe_load(handle)
    validate_portfolio(data)
    return data


def validate_portfolio(data: dict[str, Any]) -> None:
    desks = data.get("desks", [])
    instruments = data.get("instruments", [])
    risk_factors = data.get("risk_factors", [])
    if not desks:
        raise PortfolioValidationError("Portfolio must define at least one trading desk.")
    if not instruments:
        raise PortfolioValidationError("Portfolio must define at least one instrument.")

    desk_ids = {desk.get("desk_id") for desk in desks}
    if None in desk_ids or "" in desk_ids:
        raise PortfolioValidationError("Every trading desk requires a desk_id.")

    seen_instruments: set[str] = set()
    for raw in instruments:
        instrument = Instrument.from_mapping(raw)
        _validate_instrument(instrument, desk_ids, seen_instruments)
        seen_instruments.add(instrument.instrument_id)

    _validate_risk_factors(risk_factors, seen_instruments)


def build_instrument_scope(data: dict[str, Any]) -> list[dict[str, Any]]:
    validate_portfolio(data)
    risk_factors_by_instrument: dict[str, list[str]] = {}
    for risk_factor in data["risk_factors"]:
        for instrument_id in risk_factor["source_instrument_ids"]:
            risk_factors_by_instrument.setdefault(instrument_id, []).append(
                risk_factor["risk_factor_id"]
            )

    scoped: list[dict[str, Any]] = []
    for raw in data["instruments"]:
        instrument = Instrument.from_mapping(raw)
        scoped.append(
            {
                "instrument_id": instrument.instrument_id,
                "desk_id": instrument.desk_id,
                "trading_book_flag": instrument.trading_book_flag,
                "primary_risk_class": instrument.primary_risk_class,
                "risk_factor_ids": tuple(
                    risk_factors_by_instrument.get(instrument.instrument_id, [])
                ),
                "drc_relevant": instrument.drc_relevant,
                "rrao_candidate": instrument.rrao_candidate,
            }
        )
    return scoped


def _validate_instrument(
    instrument: Instrument,
    desk_ids: set[str],
    seen_instruments: set[str],
) -> None:
    if instrument.instrument_id in seen_instruments:
        raise PortfolioValidationError(f"Duplicate instrument_id: {instrument.instrument_id}")
    if instrument.desk_id not in desk_ids:
        raise PortfolioValidationError(
            f"Instrument {instrument.instrument_id} references unknown desk_id {instrument.desk_id}"
        )
    if not instrument.currency:
        raise PortfolioValidationError(
            f"Instrument {instrument.instrument_id} is missing currency."
        )
    if instrument.notional <= 0:
        raise PortfolioValidationError(
            f"Instrument {instrument.instrument_id} has invalid notional {instrument.notional}."
        )
    if instrument.trading_book_flag is None:
        raise PortfolioValidationError(
            f"Instrument {instrument.instrument_id} must set trading_book_flag explicitly."
        )
    if instrument.securitisation_flag:
        raise PortfolioValidationError(
            f"Securitisation instrument {instrument.instrument_id} is outside selected scope."
        )
    if instrument.primary_risk_class not in SUPPORTED_RISK_CLASSES:
        raise PortfolioValidationError(
            f"Instrument {instrument.instrument_id} has unsupported risk class "
            f"{instrument.primary_risk_class}."
        )

    expected_risk_class = SUPPORTED_INSTRUMENT_RISK_CLASS.get(instrument.instrument_type)
    if expected_risk_class is None:
        raise PortfolioValidationError(
            f"Unsupported instrument_type {instrument.instrument_type} "
            f"for {instrument.instrument_id}."
        )
    if instrument.primary_risk_class != expected_risk_class:
        raise PortfolioValidationError(
            f"Instrument {instrument.instrument_id} maps {instrument.instrument_type} "
            f"to {instrument.primary_risk_class}; expected {expected_risk_class}."
        )

    if instrument.instrument_type in MATURITY_REQUIRED_INSTRUMENT_TYPES:
        if not instrument.maturity_or_tenor or instrument.maturity_or_tenor == "not_applicable":
            raise PortfolioValidationError(
                f"Instrument {instrument.instrument_id} requires maturity_or_tenor."
            )

    should_be_optional = instrument.instrument_type in OPTION_INSTRUMENT_TYPES
    if instrument.optionality_flag != should_be_optional:
        raise PortfolioValidationError(
            f"Instrument {instrument.instrument_id} optionality_flag is inconsistent."
        )

    should_be_exotic = instrument.instrument_type in EXOTIC_INSTRUMENT_TYPES
    if instrument.exotic_flag != should_be_exotic:
        raise PortfolioValidationError(
            f"Instrument {instrument.instrument_id} exotic_flag is inconsistent."
        )
    if instrument.rrao_candidate != should_be_exotic:
        raise PortfolioValidationError(
            f"Instrument {instrument.instrument_id} RRAO candidate flag is inconsistent."
        )

    should_be_drc_relevant = instrument.instrument_type in DRC_RELEVANT_INSTRUMENT_TYPES
    if instrument.drc_relevant != should_be_drc_relevant:
        raise PortfolioValidationError(
            f"Instrument {instrument.instrument_id} DRC relevance is inconsistent."
        )


def _validate_risk_factors(risk_factors: list[dict[str, Any]], instrument_ids: set[str]) -> None:
    seen_risk_factors: set[str] = set()
    for risk_factor in risk_factors:
        risk_factor_id = risk_factor.get("risk_factor_id")
        if risk_factor_id in seen_risk_factors:
            raise PortfolioValidationError(f"Duplicate risk_factor_id: {risk_factor_id}")
        seen_risk_factors.add(risk_factor_id)

        risk_class = risk_factor.get("risk_class")
        if risk_class not in SUPPORTED_RISK_CLASSES:
            raise PortfolioValidationError(
                f"Risk factor {risk_factor_id} has unsupported risk class {risk_class}."
            )

        linked = set(risk_factor.get("source_instrument_ids", []))
        missing = linked - instrument_ids
        if missing:
            raise PortfolioValidationError(
                f"Risk factor {risk_factor_id} references unknown instruments: {sorted(missing)}"
            )
        if not linked:
            raise PortfolioValidationError(
                f"Risk factor {risk_factor_id} must reference at least one instrument."
            )
