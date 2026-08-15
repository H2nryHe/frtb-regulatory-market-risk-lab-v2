"""Selected non-securitisation DRC mechanics for Phase 4."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from frtb_lab.sensitivities.common import REPO_ROOT, load_yaml

PARAMETERS_PATH = REPO_ROOT / "configs" / "sa" / "selected_drc_parameters.yaml"
CANONICAL_PORTFOLIO_PATH = REPO_ROOT / "data" / "fixtures" / "canonical_portfolio.yaml"
DRC_CASE_PATH = REPO_ROOT / "data" / "fixtures" / "drc_case_portfolio.yaml"

ARTIFACTS = {
    "gross": REPO_ROOT / "data" / "artifacts" / "phase4_gross_jtd.csv",
    "net": REPO_ROOT / "data" / "artifacts" / "phase4_net_jtd.csv",
    "buckets": REPO_ROOT / "data" / "artifacts" / "phase4_drc_buckets.csv",
}


@dataclass(frozen=True)
class DRCExposure:
    instrument_id: str
    obligor_id: str
    obligor_type: str
    credit_quality_category: str
    seniority: str
    bond_equivalent_notional: float
    market_value: float
    cumulative_pnl: float
    remaining_maturity_years: float
    default_direction: str
    drc_bucket: str
    securitisation_flag: bool = False


@dataclass(frozen=True)
class GrossJTDResult:
    instrument_id: str
    obligor_id: str
    default_direction: str
    seniority: str
    credit_quality_category: str
    drc_bucket: str
    lgd: float
    bond_equivalent_notional: float
    market_value: float
    cumulative_pnl: float
    gross_jtd: float
    maturity_scale: float
    scaled_gross_jtd: float


@dataclass(frozen=True)
class NetJTDResult:
    obligor_id: str
    drc_bucket: str
    credit_quality_category: str
    source_instrument_ids: str
    net_long_jtd: float
    net_short_jtd: float
    netting_status: str


@dataclass(frozen=True)
class DRCBucketResult:
    drc_bucket: str
    net_long_jtd: float
    net_short_jtd: float
    weighted_long_jtd: float
    weighted_short_jtd: float
    hbr: float
    bucket_drc: float


@dataclass(frozen=True)
class DRCResult:
    gross_jtd: list[GrossJTDResult]
    net_jtd: list[NetJTDResult]
    buckets: list[DRCBucketResult]
    total_drc: float


def load_drc_parameters(path: Path = PARAMETERS_PATH) -> dict[str, Any]:
    return load_yaml(path)


def canonical_drc_exposures() -> list[DRCExposure]:
    portfolio = load_yaml(CANONICAL_PORTFOLIO_PATH)
    exposures = []
    for instrument in portfolio["instruments"]:
        metadata = instrument.get("drc_metadata")
        if metadata:
            exposures.append(
                exposure_from_mapping({"instrument_id": instrument["instrument_id"], **metadata})
            )
    return exposures


def drc_case_exposures(path: Path = DRC_CASE_PATH) -> list[DRCExposure]:
    data = load_yaml(path)
    return [exposure_from_mapping(row) for row in data["positions"]]


def exposure_from_mapping(row: dict[str, Any]) -> DRCExposure:
    return DRCExposure(
        instrument_id=str(row["instrument_id"]),
        obligor_id=str(row["obligor_id"]),
        obligor_type=str(row["obligor_type"]),
        credit_quality_category=str(row["credit_quality_category"]),
        seniority=str(row["seniority"]),
        bond_equivalent_notional=float(row["bond_equivalent_notional"]),
        market_value=float(row["market_value"]),
        cumulative_pnl=float(row["cumulative_pnl"]),
        remaining_maturity_years=float(row["remaining_maturity_years"]),
        default_direction=str(row["default_direction"]),
        drc_bucket=str(row["drc_bucket"]),
        securitisation_flag=bool(row.get("securitisation_flag", False)),
    )


def calculate_non_securitisation_drc(
    exposures: list[DRCExposure] | None = None,
    *,
    write_artifacts: bool = True,
) -> DRCResult:
    selected = exposures if exposures is not None else canonical_drc_exposures()
    gross = [gross_jtd(exposure) for exposure in selected]
    net = net_jtd_by_obligor(gross)
    buckets = bucket_results(net)
    result = DRCResult(
        gross_jtd=gross,
        net_jtd=net,
        buckets=buckets,
        total_drc=sum(bucket.bucket_drc for bucket in buckets),
    )
    if write_artifacts:
        write_drc_artifacts(result)
    return result


def gross_jtd(exposure: DRCExposure) -> GrossJTDResult:
    validate_drc_scope(exposure)
    params = load_drc_parameters()
    lgd = lgd_for_seniority(exposure.seniority, params)
    raw = lgd * exposure.bond_equivalent_notional + exposure.cumulative_pnl
    if exposure.default_direction == "long":
        gross = max(raw, 0.0)
    elif exposure.default_direction == "short":
        gross = min(raw, 0.0)
    else:
        raise ValueError(f"Unsupported default direction: {exposure.default_direction}")
    scale = maturity_scale(exposure.remaining_maturity_years, params)
    return GrossJTDResult(
        instrument_id=exposure.instrument_id,
        obligor_id=exposure.obligor_id,
        default_direction=exposure.default_direction,
        seniority=exposure.seniority,
        credit_quality_category=exposure.credit_quality_category,
        drc_bucket=exposure.drc_bucket,
        lgd=lgd,
        bond_equivalent_notional=exposure.bond_equivalent_notional,
        market_value=exposure.market_value,
        cumulative_pnl=exposure.cumulative_pnl,
        gross_jtd=gross,
        maturity_scale=scale,
        scaled_gross_jtd=gross * scale,
    )


def validate_drc_scope(exposure: DRCExposure) -> None:
    params = load_drc_parameters()
    if exposure.securitisation_flag:
        raise ValueError(f"Securitisation DRC is outside selected scope: {exposure.instrument_id}")
    if exposure.drc_bucket not in set(params["buckets"]["supported"]):
        raise ValueError(f"Unsupported non-securitisation DRC bucket: {exposure.drc_bucket}")
    if exposure.obligor_type not in {"corporate", "sovereign", "local_government_municipality"}:
        raise ValueError(f"Unsupported selected obligor type: {exposure.obligor_type}")
    risk_weight_for_credit_quality(exposure.credit_quality_category, params)
    lgd_for_seniority(exposure.seniority, params)


def lgd_for_seniority(seniority: str, params: dict[str, Any] | None = None) -> float:
    parameters = params or load_drc_parameters()
    if seniority == "equity_or_non_senior_debt":
        return float(parameters["lgd"]["equity_or_non_senior_debt"])
    if seniority == "senior_debt":
        return float(parameters["lgd"]["senior_debt"])
    if seniority == "covered_bond":
        return float(parameters["lgd"]["covered_bond"])
    raise ValueError(f"Unsupported selected seniority: {seniority}")


def maturity_scale(years: float, params: dict[str, Any] | None = None) -> float:
    parameters = params or load_drc_parameters()
    capital_horizon = float(parameters["maturity_scaling"]["capital_horizon_years"])
    floor = float(parameters["maturity_scaling"]["minimum_maturity_years"])
    if years >= capital_horizon:
        return 1.0
    return max(years, floor)


def risk_weight_for_credit_quality(
    credit_quality_category: str,
    params: dict[str, Any] | None = None,
) -> float:
    parameters = params or load_drc_parameters()
    weights = parameters["credit_quality_risk_weights"]
    if credit_quality_category not in weights:
        raise ValueError(f"Unsupported credit quality category: {credit_quality_category}")
    return float(weights[credit_quality_category])


def net_jtd_by_obligor(gross_results: list[GrossJTDResult]) -> list[NetJTDResult]:
    by_obligor: dict[str, list[GrossJTDResult]] = {}
    for result in gross_results:
        by_obligor.setdefault(result.obligor_id, []).append(result)

    netted = []
    for obligor_id, rows in sorted(by_obligor.items()):
        long_rows = [row for row in rows if row.scaled_gross_jtd > 0.0]
        short_rows = [row for row in rows if row.scaled_gross_jtd < 0.0]
        long_remaining = [row.scaled_gross_jtd for row in long_rows]
        short_remaining = [abs(row.scaled_gross_jtd) for row in short_rows]
        permitted = 0.0
        rejected = 0.0
        for short_index, short in enumerate(short_rows):
            matched = False
            for long_index, long in enumerate(long_rows):
                if long_remaining[long_index] <= 0.0:
                    continue
                if not seniority_offset_permitted(long.seniority, short.seniority):
                    continue
                amount = min(long_remaining[long_index], short_remaining[short_index])
                long_remaining[long_index] -= amount
                short_remaining[short_index] -= amount
                permitted += amount
                matched = True
                if short_remaining[short_index] == 0.0:
                    break
            if long_rows and not matched and short_remaining[short_index] > 0.0:
                rejected += short_remaining[short_index]
        net_long = sum(long_remaining)
        net_short = -sum(short_remaining)
        statuses = []
        if permitted:
            statuses.append(f"PERMITTED_OFFSET={permitted:.10f}")
        if rejected:
            statuses.append(f"REJECTED_OFFSET={rejected:.10f}")
        if not statuses:
            statuses.append("NO_OFFSET")
        netted.append(
            NetJTDResult(
                obligor_id=obligor_id,
                drc_bucket=rows[0].drc_bucket,
                credit_quality_category=rows[0].credit_quality_category,
                source_instrument_ids="|".join(row.instrument_id for row in rows),
                net_long_jtd=net_long,
                net_short_jtd=net_short,
                netting_status=";".join(statuses),
            )
        )
    return netted


def seniority_offset_permitted(long_seniority: str, short_seniority: str) -> bool:
    ranks = load_drc_parameters()["seniority"]["rank_low_to_high"]
    if long_seniority not in ranks or short_seniority not in ranks:
        raise ValueError(f"Unsupported seniority pair: {long_seniority}, {short_seniority}")
    return int(ranks[short_seniority]) <= int(ranks[long_seniority])


def hedge_benefit_ratio(net_long_jtd: float, net_short_jtd: float) -> float:
    denominator = net_long_jtd + abs(net_short_jtd)
    if denominator == 0.0:
        return 0.0
    return net_long_jtd / denominator


def bucket_results(net_results: list[NetJTDResult]) -> list[DRCBucketResult]:
    by_bucket: dict[str, list[NetJTDResult]] = {}
    for result in net_results:
        by_bucket.setdefault(result.drc_bucket, []).append(result)

    outputs = []
    for bucket, rows in sorted(by_bucket.items()):
        net_long = sum(row.net_long_jtd for row in rows)
        net_short = sum(row.net_short_jtd for row in rows)
        hbr = hedge_benefit_ratio(net_long, net_short)
        weighted_long = sum(
            risk_weight_for_credit_quality(row.credit_quality_category) * row.net_long_jtd
            for row in rows
        )
        weighted_short = sum(
            risk_weight_for_credit_quality(row.credit_quality_category) * row.net_short_jtd
            for row in rows
        )
        outputs.append(
            DRCBucketResult(
                drc_bucket=bucket,
                net_long_jtd=net_long,
                net_short_jtd=net_short,
                weighted_long_jtd=weighted_long,
                weighted_short_jtd=weighted_short,
                hbr=hbr,
                bucket_drc=max(weighted_long - hbr * abs(weighted_short), 0.0),
            )
        )
    return outputs


def write_drc_artifacts(result: DRCResult) -> None:
    for path in ARTIFACTS.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    _write_dataclass_csv(ARTIFACTS["gross"], result.gross_jtd)
    _write_dataclass_csv(ARTIFACTS["net"], result.net_jtd)
    _write_dataclass_csv(ARTIFACTS["buckets"], result.buckets)


def _write_dataclass_csv(path: Path, rows: list[Any]) -> None:
    if not rows:
        path.write_text("")
        return
    dictionaries = [asdict(row) for row in rows]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dictionaries[0].keys()))
        writer.writeheader()
        writer.writerows(dictionaries)


if __name__ == "__main__":
    calculate_non_securitisation_drc()
