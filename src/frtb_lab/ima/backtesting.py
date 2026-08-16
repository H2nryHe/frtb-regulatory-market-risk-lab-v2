"""Selected MAR32 desk-level VaR backtesting mechanics."""

from __future__ import annotations

import csv
import datetime as dt
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from frtb_lab.ima.pnl import generate_daily_pnl, pnl_by_desk
from frtb_lab.sensitivities.common import REPO_ROOT

EXCEPTIONS_ARTIFACT = (
    REPO_ROOT / "data" / "artifacts" / "phase7_backtesting_exceptions.csv"
)
BACKTEST_RESULTS_ARTIFACT = (
    REPO_ROOT / "data" / "artifacts" / "phase7_backtesting_results.csv"
)


@dataclass(frozen=True)
class BacktestingSummary:
    desk_id: str
    confidence_level: float
    sample_start: str
    sample_end: str
    observations: int
    apl_exceptions: int
    hpl_exceptions: int
    overall_exceptions: int
    threshold: int
    threshold_status: str


def historical_var(pnl_values: list[float], confidence_level: float) -> float:
    if not pnl_values:
        raise ValueError("At least one calibration P&L observation is required.")
    losses = sorted(-float(value) for value in pnl_values)
    index = min(math.ceil(len(losses) * confidence_level) - 1, len(losses) - 1)
    return max(losses[index], 0.0)


def is_exception(pnl: float | None, var: float | None) -> bool:
    if pnl is None or var is None:
        return True
    return -float(pnl) > float(var)


def desk_backtest_threshold(confidence_level: float) -> int:
    if confidence_level == 0.99:
        return 12
    if confidence_level == 0.975:
        return 30
    raise ValueError(f"Unsupported desk-level confidence level: {confidence_level}")


def threshold_status(confidence_level: float, overall_exceptions: int) -> str:
    if confidence_level == 0.99:
        return "BREACH" if overall_exceptions > 12 else "PASS"
    if confidence_level == 0.975:
        return "BREACH" if overall_exceptions >= 30 else "PASS"
    raise ValueError(f"Unsupported desk-level confidence level: {confidence_level}")


def backtesting_sample(
    desk_rows: list[dict[str, Any]],
    *,
    observations: int = 250,
) -> list[dict[str, Any]]:
    return sorted(desk_rows, key=lambda row: row["date"])[-observations:]


def calibration_rows_for_date(
    desk_rows: list[dict[str, Any]],
    test_date: str | dt.date,
) -> list[dict[str, Any]]:
    date = _as_date(test_date)
    start = _previous_12m_start_for_backtest(date)
    return [
        row
        for row in sorted(desk_rows, key=lambda item: item["date"])
        if start <= _as_date(row["date"]) < date
    ]


def calculate_backtesting(
    pnl_rows: list[dict[str, Any]] | None = None,
    *,
    write_artifacts: bool = True,
) -> dict[str, Any]:
    rows = pnl_rows or generate_daily_pnl()
    grouped = pnl_by_desk(rows)
    exception_rows = []
    summaries = []
    for desk_id, desk_rows in grouped.items():
        sample = backtesting_sample(desk_rows)
        for confidence_level in (0.975, 0.99):
            apl_count = 0
            hpl_count = 0
            for row in sample:
                calibration = calibration_rows_for_date(desk_rows, row["date"])
                calibration_start = calibration[0]["date"] if calibration else ""
                calibration_end = calibration[-1]["date"] if calibration else ""
                var_forecast = (
                    historical_var([float(item["hpl"]) for item in calibration], confidence_level)
                    if calibration
                    else None
                )
                apl_exception = is_exception(float(row["apl"]), var_forecast)
                hpl_exception = is_exception(float(row["hpl"]), var_forecast)
                missing_data_exception = var_forecast is None
                apl_count += int(apl_exception)
                hpl_count += int(hpl_exception)
                exception_rows.append(
                    {
                        "date": row["date"],
                        "desk_id": desk_id,
                        "confidence_level": confidence_level,
                        "var_forecast": var_forecast if var_forecast is not None else "",
                        "apl": row["apl"],
                        "hpl": row["hpl"],
                        "apl_exception": apl_exception,
                        "hpl_exception": hpl_exception,
                        "missing_data_exception": missing_data_exception,
                        "calibration_start": calibration_start,
                        "calibration_end": calibration_end,
                        "calibration_observations": len(calibration),
                        "notes": "No lookahead: test-day P&L excluded from VaR calibration.",
                    }
                )
            overall = max(apl_count, hpl_count)
            summaries.append(
                BacktestingSummary(
                    desk_id=desk_id,
                    confidence_level=confidence_level,
                    sample_start=sample[0]["date"],
                    sample_end=sample[-1]["date"],
                    observations=len(sample),
                    apl_exceptions=apl_count,
                    hpl_exceptions=hpl_count,
                    overall_exceptions=overall,
                    threshold=desk_backtest_threshold(confidence_level),
                    threshold_status=threshold_status(confidence_level, overall),
                )
            )
    if write_artifacts:
        write_exception_artifact(exception_rows)
        write_backtesting_summary_artifact(summaries)
    return {"exceptions": exception_rows, "summaries": summaries}


def write_exception_artifact(
    rows: list[dict[str, Any]],
    path: Path = EXCEPTIONS_ARTIFACT,
) -> None:
    _write_dict_csv(path, rows)


def write_backtesting_summary_artifact(
    rows: list[BacktestingSummary],
    path: Path = BACKTEST_RESULTS_ARTIFACT,
) -> None:
    _write_dict_csv(path, [row.__dict__ for row in rows])


def _previous_12m_start_for_backtest(test_date: dt.date) -> dt.date:
    try:
        one_year_prior = test_date.replace(year=test_date.year - 1)
    except ValueError:
        one_year_prior = test_date.replace(year=test_date.year - 1, day=28)
    return one_year_prior


def _as_date(value: str | dt.date) -> dt.date:
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(value)


def _write_dict_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    calculate_backtesting()
