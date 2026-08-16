"""Deterministic synthetic risk-factor history for Phase 5 IMA ES mechanics."""

from __future__ import annotations

import csv
import datetime as dt
import math
from pathlib import Path
from typing import Any

import numpy as np

from frtb_lab.sensitivities.common import REPO_ROOT, load_yaml

CONFIG_PATH = REPO_ROOT / "configs" / "ima" / "synthetic_history.yaml"
ARTIFACT_PATH = REPO_ROOT / "data" / "artifacts" / "phase5_synthetic_history.csv"


def load_history_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return load_yaml(path)


def generate_synthetic_history(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = config or load_history_config()
    metadata = cfg["metadata"]
    dates = _business_dates(
        dt.date.fromisoformat(metadata["start_date"]),
        dt.date.fromisoformat(metadata["end_date"]),
    )
    factors = list(cfg["correlation_matrix"]["factor_order"])
    sigmas = np.array([cfg["risk_factors"][factor]["daily_sigma"] for factor in factors])
    corr = np.array(cfg["correlation_matrix"]["values"], dtype=float)
    rng = np.random.default_rng(int(metadata["fixed_random_seed"]))
    values = np.array(
        [cfg["risk_factors"][factor]["initial_value"] for factor in factors],
        dtype=float,
    )
    rows = []
    for index, date in enumerate(dates):
        if index > 0:
            multiplier = _volatility_multiplier(date, cfg["regimes"])
            cov = np.outer(sigmas, sigmas) * corr * multiplier * multiplier
            shock = rng.multivariate_normal(np.zeros(len(factors)), cov)
            values = _apply_daily_shocks(values, shock, factors, cfg)
        row = {"date": date.isoformat()}
        row.update({factor: float(values[position]) for position, factor in enumerate(factors)})
        rows.append(row)
    return rows


def ten_day_shocks(
    history: list[dict[str, Any]],
    *,
    window_days: int = 10,
) -> list[dict[str, Any]]:
    cfg = load_history_config()
    factors = list(cfg["correlation_matrix"]["factor_order"])
    shocks = []
    for start in range(0, len(history) - window_days):
        end = start + window_days
        row = {
            "start_date": history[start]["date"],
            "end_date": history[end]["date"],
        }
        for factor in factors:
            convention = cfg["risk_factors"][factor]["shock_convention"]
            start_value = float(history[start][factor])
            end_value = float(history[end][factor])
            if convention == "log_price_change":
                row[factor] = math.log(end_value / start_value)
            else:
                row[factor] = end_value - start_value
        shocks.append(row)
    return shocks


def current_period_shocks(
    shocks: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[dict]:
    cfg = config or load_history_config()
    start = cfg["metadata"]["current_period_start"]
    end = cfg["metadata"]["current_period_end"]
    return [row for row in shocks if start <= row["end_date"] <= end]


def write_history_artifact(rows: list[dict[str, Any]], path: Path = ARTIFACT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _business_dates(start: dt.date, end: dt.date) -> list[dt.date]:
    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            dates.append(current)
        current += dt.timedelta(days=1)
    return dates


def _volatility_multiplier(date: dt.date, regimes: list[dict[str, Any]]) -> float:
    multiplier = 1.0
    for regime in regimes:
        start = dt.date.fromisoformat(regime["start_date"])
        end = dt.date.fromisoformat(regime["end_date"])
        if start <= date <= end:
            multiplier = max(multiplier, float(regime["volatility_multiplier"]))
    return multiplier


def _apply_daily_shocks(
    values: np.ndarray,
    shocks: np.ndarray,
    factors: list[str],
    config: dict[str, Any],
) -> np.ndarray:
    updated = values.copy()
    for index, factor in enumerate(factors):
        convention = config["risk_factors"][factor]["shock_convention"]
        if convention == "log_price_change":
            updated[index] = values[index] * math.exp(float(shocks[index]))
        else:
            updated[index] = max(values[index] + float(shocks[index]), 0.0001)
    return updated


if __name__ == "__main__":
    write_history_artifact(generate_synthetic_history())
