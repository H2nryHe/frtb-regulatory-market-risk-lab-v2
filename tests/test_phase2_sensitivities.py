from __future__ import annotations

import csv
from pathlib import Path

import pytest

from frtb_lab.mapping.buckets import equity_bucket, fx_bucket, girr_bucket
from frtb_lab.pricing.equity import black_scholes_call, black_scholes_call_delta
from frtb_lab.pricing.fx import (
    garman_kohlhagen_call,
    garman_kohlhagen_call_delta,
)
from frtb_lab.pricing.rates import fixed_rate_bond_value
from frtb_lab.sensitivities.common import load_market_state, load_parameters
from frtb_lab.sensitivities.equity import equity_spot_delta_sensitivity
from frtb_lab.sensitivities.fx import fx_delta_sensitivity
from frtb_lab.sensitivities.generate import generate_phase2_sensitivities
from frtb_lab.sensitivities.girr import girr_pv01_sensitivity
from frtb_lab.sensitivities.vega import (
    equity_option_model_vega,
    fx_option_model_vega,
    maturity_allocation,
    regulatory_vega_sensitivity,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = REPO_ROOT / "data" / "fixtures" / "canonical_portfolio.yaml"
PARAMETER_CROSSWALK = REPO_ROOT / "regulatory" / "parameter_crosswalk.csv"


@pytest.fixture()
def market_state() -> dict:
    return load_market_state()


@pytest.fixture()
def parameters() -> dict:
    return load_parameters()


def implemented_parameters() -> dict[str, dict[str, str]]:
    with PARAMETER_CROSSWALK.open(newline="") as handle:
        return {row["parameter_id"]: row for row in csv.DictReader(handle)}


def generated_rows(tmp_path: Path) -> list[dict[str, str]]:
    artifact = tmp_path / "phase2_raw_sensitivities.csv"
    generate_phase2_sensitivities(artifact)
    with artifact.open(newline="") as handle:
        return list(csv.DictReader(handle))


def terms(market_state: dict, instrument_id: str) -> dict:
    return market_state["instrument_terms"][instrument_id]


def test_drc_csr_nomenclature_audit_passes() -> None:
    import yaml

    with PORTFOLIO_PATH.open() as handle:
        portfolio = yaml.safe_load(handle)
    corp = next(row for row in portfolio["instruments"] if row["instrument_id"] == "SYN_CORP_BOND")
    assert corp["primary_risk_class"] == "CSR_NON_SECURITISATION"
    assert corp["drc_relevant"] is True
    assert corp["primary_risk_class"] not in {"DRC", "Credit/DRC", "Credit_DRC"}


def test_rrao_is_not_primary_risk_class() -> None:
    import yaml

    with PORTFOLIO_PATH.open() as handle:
        portfolio = yaml.safe_load(handle)
    barrier = next(
        row for row in portfolio["instruments"] if row["instrument_id"] == "SYN_EQ_BARRIER"
    )
    assert barrier["primary_risk_class"] == "EQUITY"
    assert barrier["rrao_candidate"] is True
    assert barrier["primary_risk_class"] != "RRAO"


def test_canonical_market_state_loads_deterministically(market_state: dict) -> None:
    assert market_state["metadata"]["synthetic"] is True
    assert market_state["metadata"]["valuation_date"] == "2026-08-15"
    assert market_state["metadata"]["reporting_currency"] == "USD"


def test_reporting_currency_is_explicit(market_state: dict) -> None:
    assert market_state["metadata"]["reporting_currency"] == "USD"
    assert market_state["metadata"]["quote_conventions"]["eurusd"] == "USD per EUR"


def test_girr_prescribed_tenor_taxonomy_matches_config(parameters: dict) -> None:
    assert parameters["girr"]["prescribed_delta_tenors_years"] == [
        0.25,
        0.5,
        1.0,
        2.0,
        3.0,
        5.0,
        10.0,
        15.0,
        20.0,
        30.0,
    ]


def test_girr_1bp_bump_and_units(market_state: dict, parameters: dict) -> None:
    instrument = terms(market_state, "SYN_USD_GOVT_5Y")
    bump = parameters["conventions"]["girr_delta_bump_absolute"]
    raw = girr_pv01_sensitivity(
        instrument_id="SYN_USD_GOVT_5Y",
        instrument=instrument,
        market_state=market_state,
        bump_size=bump,
    )
    base_rate = market_state["rates"]["USD"]["zero_curve"]["5Y"]
    base_value = fixed_rate_bond_value(
        notional=1_000_000,
        coupon_rate=instrument["coupon_rate"],
        maturity_years=instrument["maturity_years"],
        zero_rate=base_rate,
        payment_frequency_per_year=instrument["payment_frequency_per_year"],
    )
    bumped_value = fixed_rate_bond_value(
        notional=1_000_000,
        coupon_rate=instrument["coupon_rate"],
        maturity_years=instrument["maturity_years"],
        zero_rate=base_rate + 0.0001,
        payment_frequency_per_year=instrument["payment_frequency_per_year"],
    )
    assert raw == pytest.approx((bumped_value - base_value) / 0.0001)
    assert raw < 0.0


def test_irs_sensitivity_is_deterministic(market_state: dict, parameters: dict) -> None:
    kwargs = {
        "instrument_id": "SYN_USD_IRS_5Y",
        "instrument": terms(market_state, "SYN_USD_IRS_5Y"),
        "market_state": market_state,
        "bump_size": parameters["conventions"]["girr_delta_bump_absolute"],
    }
    assert girr_pv01_sensitivity(**kwargs) == pytest.approx(girr_pv01_sensitivity(**kwargs))


def test_equity_relative_shock_and_linear_sensitivity(market_state: dict, parameters: dict) -> None:
    assert parameters["conventions"]["equity_delta_shock_relative"] == 0.01
    raw = equity_spot_delta_sensitivity(
        instrument_id="SYN_EQ_INDEX",
        instrument=terms(market_state, "SYN_EQ_INDEX"),
        market_state=market_state,
        relative_shock=0.01,
    )
    assert raw == pytest.approx(750_000.0)


def test_equity_option_delta_independent_check(market_state: dict) -> None:
    instrument = terms(market_state, "SYN_EQ_CALL")
    raw = equity_spot_delta_sensitivity(
        instrument_id="SYN_EQ_CALL",
        instrument=instrument,
        market_state=market_state,
    )
    equity_state = market_state["equity"]["SYN_SPX_INDEX"]
    analytic = black_scholes_call_delta(
        spot=equity_state["spot"],
        strike=instrument["strike"],
        maturity_years=instrument["maturity_years"],
        rate=market_state["rates"]["USD"]["zero_curve"]["1Y"],
        dividend_yield=equity_state["dividend_yield"],
        volatility=equity_state["implied_volatility"]["1Y"],
        units=instrument["units"],
    )
    assert raw == pytest.approx(analytic * equity_state["spot"], rel=0.03)


def test_fx_relative_shock_orientation_and_forward_sign(
    market_state: dict,
    parameters: dict,
) -> None:
    assert parameters["conventions"]["fx_delta_shock_relative"] == 0.01
    raw = fx_delta_sensitivity(
        instrument_id="SYN_EURUSD_FWD",
        instrument=terms(market_state, "SYN_EURUSD_FWD"),
        market_state=market_state,
    )
    assert raw > 0.0
    fx_state = market_state["fx"]["EURUSD"]
    assert fx_state["spot"] == 1.10
    assert market_state["metadata"]["quote_conventions"]["eurusd"] == "USD per EUR"


def test_fx_option_delta_independent_check(market_state: dict) -> None:
    instrument = terms(market_state, "SYN_EURUSD_CALL")
    raw = fx_delta_sensitivity(
        instrument_id="SYN_EURUSD_CALL",
        instrument=instrument,
        market_state=market_state,
    )
    fx_state = market_state["fx"]["EURUSD"]
    analytic = garman_kohlhagen_call_delta(
        spot=fx_state["spot"],
        strike=instrument["strike"],
        maturity_years=instrument["maturity_years"],
        domestic_rate=fx_state["domestic_rate"],
        foreign_rate=fx_state["foreign_rate"],
        volatility=fx_state["implied_volatility"]["1Y"],
        foreign_notional=instrument["foreign_notional"],
    )
    assert raw == pytest.approx(analytic * fx_state["spot"], rel=0.04)


def test_pricing_model_vega_is_distinct_from_regulatory_vega(market_state: dict) -> None:
    instrument = terms(market_state, "SYN_EQ_CALL")
    model_vega = equity_option_model_vega(instrument=instrument, market_state=market_state)
    vol = market_state["equity"]["SYN_SPX_INDEX"]["implied_volatility"]["1Y"]
    regulatory = regulatory_vega_sensitivity(model_vega=model_vega, implied_volatility=vol)
    assert regulatory == pytest.approx(model_vega * vol)
    assert regulatory != pytest.approx(model_vega)


def test_equity_option_regulatory_vega_independent_check(market_state: dict) -> None:
    instrument = terms(market_state, "SYN_EQ_CALL")
    equity_state = market_state["equity"]["SYN_SPX_INDEX"]
    bump = 0.0001
    up = black_scholes_call(
        spot=equity_state["spot"],
        strike=instrument["strike"],
        maturity_years=instrument["maturity_years"],
        rate=market_state["rates"]["USD"]["zero_curve"]["1Y"],
        dividend_yield=equity_state["dividend_yield"],
        volatility=equity_state["implied_volatility"]["1Y"] + bump,
        units=instrument["units"],
    )
    down = black_scholes_call(
        spot=equity_state["spot"],
        strike=instrument["strike"],
        maturity_years=instrument["maturity_years"],
        rate=market_state["rates"]["USD"]["zero_curve"]["1Y"],
        dividend_yield=equity_state["dividend_yield"],
        volatility=equity_state["implied_volatility"]["1Y"] - bump,
        units=instrument["units"],
    )
    finite_vega = (up - down) / (2.0 * bump)
    regulatory = regulatory_vega_sensitivity(
        model_vega=equity_option_model_vega(instrument=instrument, market_state=market_state),
        implied_volatility=equity_state["implied_volatility"]["1Y"],
    )
    assert regulatory == pytest.approx(
        finite_vega * equity_state["implied_volatility"]["1Y"],
        rel=1e-6,
    )


def test_fx_option_regulatory_vega_independent_check(market_state: dict) -> None:
    instrument = terms(market_state, "SYN_EURUSD_CALL")
    fx_state = market_state["fx"]["EURUSD"]
    bump = 0.0001
    up = garman_kohlhagen_call(
        spot=fx_state["spot"],
        strike=instrument["strike"],
        maturity_years=instrument["maturity_years"],
        domestic_rate=fx_state["domestic_rate"],
        foreign_rate=fx_state["foreign_rate"],
        volatility=fx_state["implied_volatility"]["1Y"] + bump,
        foreign_notional=instrument["foreign_notional"],
    )
    down = garman_kohlhagen_call(
        spot=fx_state["spot"],
        strike=instrument["strike"],
        maturity_years=instrument["maturity_years"],
        domestic_rate=fx_state["domestic_rate"],
        foreign_rate=fx_state["foreign_rate"],
        volatility=fx_state["implied_volatility"]["1Y"] - bump,
        foreign_notional=instrument["foreign_notional"],
    )
    finite_vega = (up - down) / (2.0 * bump)
    regulatory = regulatory_vega_sensitivity(
        model_vega=fx_option_model_vega(instrument=instrument, market_state=market_state),
        implied_volatility=fx_state["implied_volatility"]["1Y"],
    )
    assert regulatory == pytest.approx(finite_vega * fx_state["implied_volatility"]["1Y"], rel=1e-6)


def test_option_maturity_mapping_exact_and_between_tenor(parameters: dict) -> None:
    tenors = parameters["vega"]["option_maturity_tenors_years"]
    assert maturity_allocation(1.0, tenors) == {1.0: 1.0}
    assert maturity_allocation(2.0, tenors) == {1.0: 0.5, 3.0: 0.5}


def test_selected_bucket_mapping_works(market_state: dict) -> None:
    equity_state = market_state["equity"]["SYN_SPX_INDEX"]
    assert girr_bucket("USD") == "USD"
    assert equity_bucket("SYN_SPX_INDEX", equity_state["synthetic_bucket_assumption"]) == (
        "EQUITY_BUCKET_12"
    )
    assert fx_bucket("EURUSD", "USD") == "EUR/USD"


def test_every_implemented_artifact_risk_weight_has_parameter_crosswalk(tmp_path: Path) -> None:
    rows = generated_rows(tmp_path)
    params = implemented_parameters()
    for row in rows:
        parameter = params[row["source_parameter_id"]]
        assert parameter["implementation_status"] == "IMPLEMENTED"
        assert parameter["source_id"] == "BIS_MAR21"
        assert parameter["source_paragraph_or_table"]


def test_weighted_sensitivity_equals_raw_times_sourced_weight(tmp_path: Path) -> None:
    for row in generated_rows(tmp_path):
        raw = float(row["raw_sensitivity"])
        risk_weight = float(row["risk_weight"])
        weighted = float(row["weighted_sensitivity"])
        assert weighted == pytest.approx(raw * risk_weight)


def test_no_secondary_domain_parameter_sources() -> None:
    for row in implemented_parameters().values():
        if row["implementation_status"] == "IMPLEMENTED" and row["component"].startswith(
            "Phase2"
        ):
            assert row["source_id"] == "BIS_MAR21"
            assert row["source_paragraph_or_table"].startswith("MAR21")


def test_no_out_of_scope_drc_rrao_or_generic_capital_artifacts_exist() -> None:
    forbidden_paths = [
        REPO_ROOT / "src" / "frtb_lab" / "sa" / "securitisation_drc.py",
        REPO_ROOT / "src" / "frtb_lab" / "sa" / "ctp.py",
        REPO_ROOT / "src" / "frtb_lab" / "sa" / "ima",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "default_risk.py",
        REPO_ROOT / "data" / "artifacts" / "sbm_capital.csv",
        REPO_ROOT / "data" / "artifacts" / "drc_capital.csv",
        REPO_ROOT / "data" / "artifacts" / "rrao_capital.csv",
        REPO_ROOT / "data" / "artifacts" / "ima_capital.csv",
        REPO_ROOT / "data" / "artifacts" / "phase8_bank_capital.csv",
    ]
    assert not any(path.exists() for path in forbidden_paths)


def test_generated_rows_are_raw_or_weighted_only(tmp_path: Path) -> None:
    rows = generated_rows(tmp_path)
    assert {row["sensitivity_type"] for row in rows} == {"delta", "vega"}
    assert not any("capital" in key.lower() for row in rows for key in row)
    assert not any("bucket capital" in row["notes"].lower() for row in rows)


def test_curvature_is_preparation_only() -> None:
    params = implemented_parameters()
    assert params["CURVATURE_SELECTED_PROVENANCE"]["implementation_status"] == (
        "VERIFIED_NOT_IMPLEMENTED"
    )
