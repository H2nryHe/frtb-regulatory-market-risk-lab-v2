"""Phase 1 instrument records.

These classes intentionally hold regulatory taxonomy metadata only. They do not
price instruments, calculate sensitivities, or produce capital measures.
"""

from __future__ import annotations

from dataclasses import dataclass


class InstrumentValidationError(ValueError):
    """Raised when a synthetic instrument violates Phase 1 scope rules."""


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    instrument_type: str
    desk_id: str
    currency: str
    notional: float
    primary_risk_class: str
    underlier_or_issuer: str | None = None
    maturity_or_tenor: str | None = None
    reference_value: float | None = None
    trading_book_flag: bool | None = None
    optionality_flag: bool = False
    exotic_flag: bool = False
    securitisation_flag: bool = False
    drc_relevant: bool = False
    rrao_candidate: bool = False
    description: str = ""
    status: str = "ACTIVE_SYNTHETIC"
    notes: str = ""

    @classmethod
    def from_mapping(cls, row: dict) -> Instrument:
        return cls(
            instrument_id=row["instrument_id"],
            instrument_type=row["instrument_type"],
            desk_id=row["desk_id"],
            currency=row["currency"],
            notional=float(row["notional"]),
            primary_risk_class=row["primary_risk_class"],
            underlier_or_issuer=row.get("underlier_or_issuer"),
            maturity_or_tenor=row.get("maturity_or_tenor"),
            reference_value=_optional_float(row.get("reference_value")),
            trading_book_flag=row.get("trading_book_flag"),
            optionality_flag=bool(row.get("optionality_flag", False)),
            exotic_flag=bool(row.get("exotic_flag", False)),
            securitisation_flag=bool(row.get("securitisation_flag", False)),
            drc_relevant=bool(row.get("drc_relevant", False)),
            rrao_candidate=bool(row.get("rrao_candidate", False)),
            description=row.get("description", ""),
            status=row.get("status", "ACTIVE_SYNTHETIC"),
            notes=row.get("notes", ""),
        )


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
