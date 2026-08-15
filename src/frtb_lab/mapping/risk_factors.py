"""Risk-factor taxonomy helpers for Phase 1."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskFactor:
    risk_factor_id: str
    risk_class: str
    risk_factor_type: str
    source_instrument_ids: tuple[str, ...]
    required_sensitivity_types: tuple[str, ...]
    source_id: str
    source_paragraph_or_table: str

    @classmethod
    def from_mapping(cls, row: dict) -> RiskFactor:
        return cls(
            risk_factor_id=row["risk_factor_id"],
            risk_class=row["risk_class"],
            risk_factor_type=row["risk_factor_type"],
            source_instrument_ids=tuple(row["source_instrument_ids"]),
            required_sensitivity_types=tuple(row["required_sensitivity_types"]),
            source_id=row["source_id"],
            source_paragraph_or_table=row["source_paragraph_or_table"],
        )
