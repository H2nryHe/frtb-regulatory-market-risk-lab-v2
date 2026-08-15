"""Selected residual risk add-on classification and calculation for Phase 4."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from frtb_lab.sensitivities.common import REPO_ROOT, load_yaml

PARAMETERS_PATH = REPO_ROOT / "configs" / "sa" / "selected_rrao_parameters.yaml"
RRAO_INVENTORY_PATH = REPO_ROOT / "governance" / "rrao_inventory.csv"
RRAO_CASE_PATH = REPO_ROOT / "data" / "fixtures" / "rrao_case_portfolio.yaml"
ARTIFACT_PATH = REPO_ROOT / "data" / "artifacts" / "phase4_rrao.csv"

OTHER_RESIDUAL_RISK = "OTHER_RESIDUAL_RISK"
EXOTIC_UNDERLYING = "EXOTIC_UNDERLYING"
NOT_IN_SCOPE = "NOT_IN_SCOPE"


@dataclass(frozen=True)
class RRAOInstrument:
    instrument_id: str
    underlying_type: str
    path_dependent: bool
    multi_underlying: bool
    other_residual_risk: bool
    exotic_underlying: bool
    listed_or_ccp_eligible: bool
    back_to_back: bool
    gross_notional: float


@dataclass(frozen=True)
class RRAOResultRow:
    instrument_id: str
    rrao_category: str
    gross_notional: float
    risk_weight: float
    included: bool
    exclusion_reason: str
    rrao_contribution: float
    source_parameter_id: str
    notes: str


@dataclass(frozen=True)
class RRAOResult:
    rows: list[RRAOResultRow]
    total_rrao: float


def load_rrao_parameters(path: Path = PARAMETERS_PATH) -> dict[str, Any]:
    return load_yaml(path)


def canonical_rrao_instruments(path: Path = RRAO_INVENTORY_PATH) -> list[RRAOInstrument]:
    with path.open(newline="") as handle:
        return [_instrument_from_csv(row) for row in csv.DictReader(handle)]


def rrao_case_instruments(path: Path = RRAO_CASE_PATH) -> list[RRAOInstrument]:
    data = load_yaml(path)
    return [instrument_from_mapping(row) for row in data["instruments"]]


def instrument_from_mapping(row: dict[str, Any]) -> RRAOInstrument:
    return RRAOInstrument(
        instrument_id=str(row["instrument_id"]),
        underlying_type=str(row["underlying_type"]),
        path_dependent=bool(row["path_dependent"]),
        multi_underlying=bool(row["multi_underlying"]),
        other_residual_risk=bool(row["other_residual_risk"]),
        exotic_underlying=bool(row["exotic_underlying"]),
        listed_or_ccp_eligible=bool(row["listed_or_ccp_eligible"]),
        back_to_back=bool(row["back_to_back"]),
        gross_notional=float(row["gross_notional"]),
    )


def calculate_rrao(
    instruments: list[RRAOInstrument] | None = None,
    *,
    write_artifact: bool = True,
) -> RRAOResult:
    selected = instruments if instruments is not None else canonical_rrao_instruments()
    rows = [classify_and_calculate(instrument) for instrument in selected]
    result = RRAOResult(
        rows=rows,
        total_rrao=sum(row.rrao_contribution for row in rows if row.included),
    )
    if write_artifact:
        write_rrao_artifact(result)
    return result


def classify_and_calculate(instrument: RRAOInstrument) -> RRAOResultRow:
    category = classify_category(instrument)
    included, exclusion_reason = inclusion_status(instrument, category)
    risk_weight, source_parameter_id = risk_weight_for_category(category)
    contribution = instrument.gross_notional * risk_weight if included else 0.0
    notes = _classification_notes(instrument, category)
    return RRAOResultRow(
        instrument_id=instrument.instrument_id,
        rrao_category=category,
        gross_notional=instrument.gross_notional,
        risk_weight=risk_weight,
        included=included,
        exclusion_reason=exclusion_reason,
        rrao_contribution=contribution,
        source_parameter_id=source_parameter_id,
        notes=notes,
    )


def classify_category(instrument: RRAOInstrument) -> str:
    if instrument.exotic_underlying:
        return EXOTIC_UNDERLYING
    if instrument.other_residual_risk or instrument.path_dependent or instrument.multi_underlying:
        return OTHER_RESIDUAL_RISK
    return NOT_IN_SCOPE


def inclusion_status(instrument: RRAOInstrument, category: str) -> tuple[bool, str]:
    if category == NOT_IN_SCOPE:
        return False, "not_subject_to_rrao"
    if instrument.back_to_back:
        return False, "exact_back_to_back"
    if category == OTHER_RESIDUAL_RISK and instrument.listed_or_ccp_eligible:
        return False, "listed_or_ccp_other_residual_risk"
    return True, ""


def risk_weight_for_category(category: str) -> tuple[float, str]:
    params = load_rrao_parameters()
    if category == EXOTIC_UNDERLYING:
        return (
            float(params["categories"]["exotic_underlying"]["risk_weight"]),
            "RRAO_RW_EXOTIC_UNDERLYING",
        )
    if category == OTHER_RESIDUAL_RISK:
        return (
            float(params["categories"]["other_residual_risk"]["risk_weight"]),
            "RRAO_RW_OTHER_RESIDUAL_RISK",
        )
    return 0.0, ""


def write_rrao_artifact(result: RRAOResult, path: Path = ARTIFACT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dictionaries = [asdict(row) for row in result.rows]
    if not dictionaries:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dictionaries[0].keys()))
        writer.writeheader()
        writer.writerows(dictionaries)


def _instrument_from_csv(row: dict[str, str]) -> RRAOInstrument:
    return RRAOInstrument(
        instrument_id=row["instrument_id"],
        underlying_type=row["underlying_type"],
        path_dependent=row["path_dependent"] == "true",
        multi_underlying=row["multi_underlying"] == "true",
        other_residual_risk=row["other_residual_risk"] == "true",
        exotic_underlying=row["exotic_underlying"] == "true",
        listed_or_ccp_eligible=row["listed_or_ccp_eligible"] == "true",
        back_to_back=row["back_to_back"] == "true",
        gross_notional=float(row["gross_notional"]),
    )


def _classification_notes(instrument: RRAOInstrument, category: str) -> str:
    if instrument.instrument_id == "SYN_EQ_BARRIER":
        return "Path-dependent barrier option: other residual risk, not exotic underlying."
    if category == EXOTIC_UNDERLYING:
        return "Underlying is outside selected SBM/DRC risk-factor universe."
    if category == OTHER_RESIDUAL_RISK:
        return "Instrument bears selected other residual risk."
    return "No selected RRAO trigger."


if __name__ == "__main__":
    calculate_rrao()
