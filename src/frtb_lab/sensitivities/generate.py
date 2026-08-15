"""Generate ignored Phase 2 raw and weighted sensitivity artifacts."""

from __future__ import annotations

import csv
from pathlib import Path

from frtb_lab.mapping.buckets import equity_bucket, fx_bucket, girr_bucket
from frtb_lab.sensitivities.common import REPO_ROOT, load_market_state, load_parameters
from frtb_lab.sensitivities.equity import equity_spot_delta_sensitivity
from frtb_lab.sensitivities.fx import fx_delta_sensitivity
from frtb_lab.sensitivities.girr import girr_pv01_sensitivity
from frtb_lab.sensitivities.vega import (
    equity_option_model_vega,
    fx_option_model_vega,
    regulatory_vega_sensitivity,
)

ARTIFACT_PATH = REPO_ROOT / "data" / "artifacts" / "phase2_raw_sensitivities.csv"

FIELDNAMES = [
    "instrument_id",
    "desk_id",
    "risk_class",
    "risk_factor_id",
    "risk_factor_type",
    "sensitivity_type",
    "regulatory_bucket",
    "regulatory_tenor",
    "raw_sensitivity",
    "sensitivity_unit",
    "risk_weight",
    "weighted_sensitivity",
    "source_parameter_id",
    "notes",
]


def generate_phase2_sensitivities(path: Path = ARTIFACT_PATH) -> list[dict[str, object]]:
    market_state = load_market_state()
    parameters = load_parameters()
    terms = market_state["instrument_terms"]
    rows = [
        *_girr_rows(terms, market_state, parameters),
        *_equity_rows(terms, market_state, parameters),
        *_fx_rows(terms, market_state, parameters),
        *_vega_rows(terms, market_state, parameters),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def _row(**kwargs: object) -> dict[str, object]:
    raw = float(kwargs["raw_sensitivity"])
    risk_weight = float(kwargs["risk_weight"])
    kwargs["raw_sensitivity"] = f"{raw:.10f}"
    kwargs["risk_weight"] = f"{risk_weight:.6f}"
    kwargs["weighted_sensitivity"] = f"{raw * risk_weight:.10f}"
    return kwargs


def _girr_rows(terms: dict, market_state: dict, parameters: dict) -> list[dict[str, object]]:
    risk_weight = parameters["girr"]["delta_risk_weights"]["5.0"]
    rows = []
    for instrument_id, desk_id in [
        ("SYN_USD_GOVT_5Y", "TD-RATES"),
        ("SYN_USD_IRS_5Y", "TD-RATES"),
    ]:
        raw = girr_pv01_sensitivity(
            instrument_id=instrument_id,
            instrument=terms[instrument_id],
            market_state=market_state,
            bump_size=parameters["conventions"]["girr_delta_bump_absolute"],
        )
        rows.append(
            _row(
                instrument_id=instrument_id,
                desk_id=desk_id,
                risk_class="GIRR",
                risk_factor_id="RF_GIRR_USD_5Y",
                risk_factor_type="risk_free_yield_curve_tenor",
                sensitivity_type="delta",
                regulatory_bucket=girr_bucket("USD"),
                regulatory_tenor="5Y",
                raw_sensitivity=raw,
                sensitivity_unit="USD per 1.0 absolute rate after 1bp bump division",
                risk_weight=risk_weight,
                source_parameter_id="GIRR_DELTA_RW_5Y",
                notes="PV01 sensitivity; no aggregation.",
            )
        )
    return rows


def _equity_rows(terms: dict, market_state: dict, parameters: dict) -> list[dict[str, object]]:
    equity_state = market_state["equity"]["SYN_SPX_INDEX"]
    bucket = equity_bucket("SYN_SPX_INDEX", equity_state["synthetic_bucket_assumption"])
    risk_weight = parameters["equity"]["delta_spot_risk_weight"]
    rows = []
    for instrument_id in ["SYN_EQ_INDEX", "SYN_EQ_CALL"]:
        raw = equity_spot_delta_sensitivity(
            instrument_id=instrument_id,
            instrument=terms[instrument_id],
            market_state=market_state,
            relative_shock=parameters["conventions"]["equity_delta_shock_relative"],
        )
        rows.append(
            _row(
                instrument_id=instrument_id,
                desk_id="TD-EQUITY",
                risk_class="EQUITY",
                risk_factor_id="RF_EQUITY_SPX_SPOT",
                risk_factor_type="equity_spot",
                sensitivity_type="delta",
                regulatory_bucket=bucket,
                regulatory_tenor="spot",
                raw_sensitivity=raw,
                sensitivity_unit="USD per 1.0 relative equity spot move",
                risk_weight=risk_weight,
                source_parameter_id="EQUITY_DELTA_BUCKET_12_SPOT_RW",
                notes="Equity repo-rate sensitivity excluded from selected Phase 2 scope.",
            )
        )
    return rows


def _fx_rows(terms: dict, market_state: dict, parameters: dict) -> list[dict[str, object]]:
    bucket = fx_bucket("EURUSD", market_state["metadata"]["reporting_currency"])
    risk_weight = parameters["fx"]["delta_risk_weight"]
    rows = []
    for instrument_id in ["SYN_EURUSD_FWD", "SYN_EURUSD_CALL"]:
        raw = fx_delta_sensitivity(
            instrument_id=instrument_id,
            instrument=terms[instrument_id],
            market_state=market_state,
            relative_shock=parameters["conventions"]["fx_delta_shock_relative"],
        )
        rows.append(
            _row(
                instrument_id=instrument_id,
                desk_id="TD-FX",
                risk_class="FX",
                risk_factor_id="RF_FX_EURUSD_SPOT",
                risk_factor_type="fx_spot",
                sensitivity_type="delta",
                regulatory_bucket=bucket,
                regulatory_tenor="spot",
                raw_sensitivity=raw,
                sensitivity_unit="USD per 1.0 relative EUR/USD move; quote is USD per EUR",
                risk_weight=risk_weight,
                source_parameter_id="FX_DELTA_BASE_RW",
                notes="Base FX risk weight used; discretionary currency-pair reduction not used.",
            )
        )
    return rows


def _vega_rows(terms: dict, market_state: dict, parameters: dict) -> list[dict[str, object]]:
    equity_state = market_state["equity"]["SYN_SPX_INDEX"]
    equity_raw = regulatory_vega_sensitivity(
        model_vega=equity_option_model_vega(
            instrument=terms["SYN_EQ_CALL"],
            market_state=market_state,
        ),
        implied_volatility=equity_state["implied_volatility"]["1Y"],
    )
    fx_state = market_state["fx"]["EURUSD"]
    fx_raw = regulatory_vega_sensitivity(
        model_vega=fx_option_model_vega(
            instrument=terms["SYN_EURUSD_CALL"],
            market_state=market_state,
        ),
        implied_volatility=fx_state["implied_volatility"]["1Y"],
    )
    return [
        _row(
            instrument_id="SYN_EQ_CALL",
            desk_id="TD-EQUITY",
            risk_class="EQUITY",
            risk_factor_id="RF_EQUITY_SPX_VOL_1Y",
            risk_factor_type="equity_implied_volatility",
            sensitivity_type="vega",
            regulatory_bucket=equity_bucket(
                "SYN_SPX_INDEX", equity_state["synthetic_bucket_assumption"]
            ),
            regulatory_tenor="1Y",
            raw_sensitivity=equity_raw,
            sensitivity_unit="USD regulatory vega = model vega per vol 1.0 times implied vol",
            risk_weight=parameters["vega"]["equity_large_cap_indices"]["risk_weight"],
            source_parameter_id="VEGA_EQUITY_LARGE_CAP_INDICES_RW",
            notes="Pricing-model vega transformed under MAR21.25.",
        ),
        _row(
            instrument_id="SYN_EURUSD_CALL",
            desk_id="TD-FX",
            risk_class="FX",
            risk_factor_id="RF_FX_EURUSD_VOL_1Y",
            risk_factor_type="fx_implied_volatility",
            sensitivity_type="vega",
            regulatory_bucket=fx_bucket("EURUSD", market_state["metadata"]["reporting_currency"]),
            regulatory_tenor="1Y",
            raw_sensitivity=fx_raw,
            sensitivity_unit="USD regulatory vega = model vega per vol 1.0 times implied vol",
            risk_weight=parameters["vega"]["fx"]["risk_weight"],
            source_parameter_id="VEGA_FX_RW",
            notes="Pricing-model vega transformed under MAR21.25.",
        ),
    ]


if __name__ == "__main__":
    generate_phase2_sensitivities()
