from __future__ import annotations

import copy
import csv
from pathlib import Path

import pytest
import yaml

from frtb_lab.mapping.scope import (
    PortfolioValidationError,
    build_instrument_scope,
    load_canonical_portfolio,
    validate_portfolio,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "data" / "fixtures" / "canonical_portfolio.yaml"
SOURCE_REGISTER = REPO_ROOT / "regulatory" / "source_register.yaml"
INSTRUMENT_INVENTORY = REPO_ROOT / "governance" / "instrument_inventory.csv"
RISK_FACTOR_INVENTORY = REPO_ROOT / "governance" / "risk_factor_inventory.csv"
SENSITIVITY_MAPPING = REPO_ROOT / "regulatory" / "sensitivity_mapping.csv"

SUPPORTED_RISK_CLASSES = {"GIRR", "EQUITY", "FX", "CREDIT"}


@pytest.fixture()
def portfolio() -> dict:
    return load_canonical_portfolio(FIXTURE_PATH)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def source_ids() -> set[str]:
    with SOURCE_REGISTER.open() as handle:
        data = yaml.safe_load(handle)
    return {source["source_id"] for source in data["sources"]}


def instrument_by_id(portfolio: dict) -> dict[str, dict]:
    return {row["instrument_id"]: row for row in portfolio["instruments"]}


def instrument_ids(portfolio: dict) -> list[str]:
    return [row["instrument_id"] for row in portfolio["instruments"]]


def test_canonical_portfolio_loads(portfolio: dict) -> None:
    assert portfolio["metadata"]["synthetic"] is True
    assert len(portfolio["desks"]) == 4
    assert len(portfolio["instruments"]) == 8


def test_all_instrument_ids_unique(portfolio: dict) -> None:
    ids = instrument_ids(portfolio)
    assert len(ids) == len(set(ids))


def test_every_instrument_references_known_desk(portfolio: dict) -> None:
    desk_ids = {desk["desk_id"] for desk in portfolio["desks"]}
    assert {instrument["desk_id"] for instrument in portfolio["instruments"]} <= desk_ids


def test_every_selected_instrument_has_explicit_trading_book_flag(portfolio: dict) -> None:
    assert all(
        isinstance(instrument["trading_book_flag"], bool)
        for instrument in portfolio["instruments"]
    )


def test_no_securitisation_enters_canonical_scope(portfolio: dict) -> None:
    assert not any(instrument["securitisation_flag"] for instrument in portfolio["instruments"])


def test_canonical_instruments_map_to_supported_risk_classes(portfolio: dict) -> None:
    assert {row["primary_risk_class"] for row in portfolio["instruments"]} <= SUPPORTED_RISK_CLASSES


def test_girr_instruments_map_consistently(portfolio: dict) -> None:
    by_id = instrument_by_id(portfolio)
    assert by_id["SYN_USD_GOVT_5Y"]["primary_risk_class"] == "GIRR"
    assert by_id["SYN_USD_IRS_5Y"]["primary_risk_class"] == "GIRR"
    girr_rfs = [rf for rf in portfolio["risk_factors"] if rf["risk_class"] == "GIRR"]
    assert {rf["risk_factor_id"] for rf in girr_rfs} == {"RF_GIRR_USD_5Y"}


def test_equity_instruments_map_consistently(portfolio: dict) -> None:
    by_id = instrument_by_id(portfolio)
    assert by_id["SYN_EQ_INDEX"]["primary_risk_class"] == "EQUITY"
    assert by_id["SYN_EQ_CALL"]["primary_risk_class"] == "EQUITY"
    assert by_id["SYN_EQ_BARRIER"]["primary_risk_class"] == "EQUITY"
    equity_rfs = {
        rf["risk_factor_id"]
        for rf in portfolio["risk_factors"]
        if rf["risk_class"] == "EQUITY"
    }
    assert equity_rfs == {"RF_EQUITY_SPX_SPOT", "RF_EQUITY_SPX_VOL_1Y"}


def test_fx_instruments_map_consistently(portfolio: dict) -> None:
    by_id = instrument_by_id(portfolio)
    assert by_id["SYN_EURUSD_FWD"]["primary_risk_class"] == "FX"
    assert by_id["SYN_EURUSD_CALL"]["primary_risk_class"] == "FX"
    fx_rfs = {rf["risk_factor_id"] for rf in portfolio["risk_factors"] if rf["risk_class"] == "FX"}
    assert fx_rfs == {"RF_FX_EURUSD_SPOT", "RF_FX_EURUSD_VOL_1Y"}


def test_corporate_credit_drc_candidate_is_explicit(portfolio: dict) -> None:
    corp = instrument_by_id(portfolio)["SYN_CORP_BOND"]
    assert corp["primary_risk_class"] == "CREDIT"
    assert corp["drc_relevant"] is True
    assert corp["securitisation_flag"] is False


def test_exotic_rrao_candidate_is_explicit(portfolio: dict) -> None:
    barrier = instrument_by_id(portfolio)["SYN_EQ_BARRIER"]
    assert barrier["optionality_flag"] is True
    assert barrier["exotic_flag"] is True
    assert barrier["rrao_candidate"] is True


def test_optionality_metadata_is_consistent(portfolio: dict) -> None:
    optional_types = {"EQUITY_OPTION", "EQUITY_BARRIER_OPTION", "FX_OPTION"}
    for instrument in portfolio["instruments"]:
        assert instrument["optionality_flag"] == (instrument["instrument_type"] in optional_types)


def test_sensitivity_mapping_exists_for_every_canonical_instrument_type(portfolio: dict) -> None:
    canonical_types = {instrument["instrument_type"] for instrument in portfolio["instruments"]}
    mapped_types = {row["instrument_type"] for row in read_csv(SENSITIVITY_MAPPING)}
    assert canonical_types <= mapped_types


def test_vanilla_options_have_future_sensitivity_requirements() -> None:
    rows = {
        row["instrument_type"]: row
        for row in read_csv(SENSITIVITY_MAPPING)
        if row["instrument_type"] in {"EQUITY_OPTION", "FX_OPTION"}
    }
    for row in rows.values():
        assert row["delta_required"] == "true"
        assert row["vega_required"] == "true"
        assert row["curvature_required"] == "true"
        assert row["drc_relevant"] == "false"


def test_build_scope_keeps_every_instrument(portfolio: dict) -> None:
    scoped = build_instrument_scope(portfolio)
    assert {row["instrument_id"] for row in scoped} == set(instrument_ids(portfolio))
    assert all(row["risk_factor_ids"] for row in scoped)


def test_governance_instrument_inventory_matches_fixture(portfolio: dict) -> None:
    inventory_ids = {row["instrument_id"] for row in read_csv(INSTRUMENT_INVENTORY)}
    assert inventory_ids == set(instrument_ids(portfolio))


def test_risk_factor_inventory_matches_fixture(portfolio: dict) -> None:
    csv_ids = {row["risk_factor_id"] for row in read_csv(RISK_FACTOR_INVENTORY)}
    fixture_ids = {row["risk_factor_id"] for row in portfolio["risk_factors"]}
    assert csv_ids == fixture_ids


def test_regulatory_source_ids_in_mapping_artifacts_exist(portfolio: dict) -> None:
    valid_ids = source_ids()
    mapping_ids = {row["source_id"] for row in read_csv(SENSITIVITY_MAPPING)}
    risk_factor_ids = {row["source_id"] for row in portfolio["risk_factors"]}
    csv_risk_factor_ids = {row["source_id"] for row in read_csv(RISK_FACTOR_INVENTORY)}
    assert mapping_ids <= valid_ids
    assert risk_factor_ids <= valid_ids
    assert csv_risk_factor_ids <= valid_ids


def test_unsupported_mapping_fails(portfolio: dict) -> None:
    bad = copy.deepcopy(portfolio)
    bad["instruments"][0]["primary_risk_class"] = "EQUITY"
    with pytest.raises(PortfolioValidationError, match="expected GIRR"):
        validate_portfolio(bad)


def test_unknown_desk_fails(portfolio: dict) -> None:
    bad = copy.deepcopy(portfolio)
    bad["instruments"][0]["desk_id"] = "TD-UNKNOWN"
    with pytest.raises(PortfolioValidationError, match="unknown desk_id"):
        validate_portfolio(bad)


def test_duplicate_instrument_id_fails(portfolio: dict) -> None:
    bad = copy.deepcopy(portfolio)
    bad["instruments"][1]["instrument_id"] = bad["instruments"][0]["instrument_id"]
    with pytest.raises(PortfolioValidationError, match="Duplicate instrument_id"):
        validate_portfolio(bad)


def test_securitisation_fixture_fails(portfolio: dict) -> None:
    bad = copy.deepcopy(portfolio)
    bad["instruments"][0]["securitisation_flag"] = True
    with pytest.raises(PortfolioValidationError, match="outside selected scope"):
        validate_portfolio(bad)


def test_inconsistent_option_metadata_fails(portfolio: dict) -> None:
    bad = copy.deepcopy(portfolio)
    bad["instruments"][3]["optionality_flag"] = False
    with pytest.raises(PortfolioValidationError, match="optionality_flag"):
        validate_portfolio(bad)


def test_inconsistent_exotic_metadata_fails(portfolio: dict) -> None:
    bad = copy.deepcopy(portfolio)
    bad["instruments"][7]["exotic_flag"] = False
    with pytest.raises(PortfolioValidationError, match="exotic_flag"):
        validate_portfolio(bad)


def test_corporate_credit_marked_drc_irrelevant_fails(portfolio: dict) -> None:
    bad = copy.deepcopy(portfolio)
    bad["instruments"][6]["drc_relevant"] = False
    with pytest.raises(PortfolioValidationError, match="DRC relevance"):
        validate_portfolio(bad)


def test_no_capital_result_or_phase2_sbm_module_exists() -> None:
    assert not (REPO_ROOT / "src" / "frtb_lab" / "sa" / "sbm.py").exists()
    assert not (REPO_ROOT / "data" / "artifacts" / "capital_result.csv").exists()
    assert not (REPO_ROOT / "data" / "artifacts" / "capital_result.yaml").exists()
