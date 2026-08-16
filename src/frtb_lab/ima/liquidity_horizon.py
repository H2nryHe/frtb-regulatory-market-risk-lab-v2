"""MAR33 selected liquidity-horizon Expected Shortfall mechanics."""

from __future__ import annotations

import csv
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from frtb_lab.ima.expected_shortfall import empirical_expected_shortfall
from frtb_lab.ima.revaluation import portfolio_pnl_vector
from frtb_lab.sensitivities.common import REPO_ROOT, load_yaml

CONFIG_PATH = REPO_ROOT / "configs" / "ima" / "liquidity_horizons.yaml"
ARTIFACT_PATH = REPO_ROOT / "data" / "artifacts" / "phase5_liquidity_horizon_es.csv"


@dataclass(frozen=True)
class LiquidityHorizonESResult:
    factor_set: str
    observation_period: str
    base_10d_es: float
    liquidity_adjusted_es: float
    es_by_horizon: dict[int, float]
    q_sets: dict[int, tuple[str, ...]]


def load_liquidity_horizon_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return load_yaml(path)


def factor_liquidity_horizons(config: dict[str, Any] | None = None) -> dict[str, int]:
    cfg = config or load_liquidity_horizon_config()
    mappings = {
        factor_id: int(mapping["liquidity_horizon_days"])
        for factor_id, mapping in cfg["selected_mappings"].items()
    }
    mappings.update(
        {
            factor_id: int(horizon)
            for factor_id, horizon in cfg["test_only_horizons"].items()
        }
    )
    return mappings


def q_sets_for_factors(
    factor_ids: set[str],
    factor_horizons: dict[str, int],
    horizon_grid: list[int] | None = None,
) -> dict[int, tuple[str, ...]]:
    grid = horizon_grid or load_liquidity_horizon_config()["horizon_grid_days"]
    output = {}
    for horizon in grid:
        output[int(horizon)] = tuple(
            sorted(factor for factor in factor_ids if factor_horizons[factor] >= int(horizon))
        )
    return output


def liquidity_horizon_expected_shortfall(
    shocks: list[dict[str, Any]],
    factor_ids: set[str],
    *,
    factor_set_name: str,
    observation_period: str,
    pnl_function: Callable[[list[dict[str, Any]], set[str]], list[float]] = portfolio_pnl_vector,
    confidence_level: float = 0.975,
) -> LiquidityHorizonESResult:
    config = load_liquidity_horizon_config()
    horizon_grid = [int(value) for value in config["horizon_grid_days"]]
    base_horizon = int(config["base_horizon_days"])
    horizons = factor_liquidity_horizons(config)
    q_sets = q_sets_for_factors(set(factor_ids), horizons, horizon_grid)
    es_by_horizon = {}
    for horizon in horizon_grid:
        subset = set(q_sets[horizon])
        if subset:
            es_by_horizon[horizon] = empirical_expected_shortfall(
                pnl_function(shocks, subset),
                confidence_level=confidence_level,
            )
        else:
            es_by_horizon[horizon] = 0.0
    base_es = es_by_horizon[base_horizon]
    radicand = base_es * base_es
    for previous, current in zip(horizon_grid, horizon_grid[1:], strict=False):
        radicand += es_by_horizon[current] ** 2 * ((current - previous) / base_horizon)
    return LiquidityHorizonESResult(
        factor_set=factor_set_name,
        observation_period=observation_period,
        base_10d_es=base_es,
        liquidity_adjusted_es=math.sqrt(max(radicand, 0.0)),
        es_by_horizon=es_by_horizon,
        q_sets=q_sets,
    )


def manual_liquidity_horizon_es(
    es_by_horizon: dict[int, float],
    *,
    base_horizon: int = 10,
    horizon_grid: list[int] | None = None,
) -> float:
    grid = horizon_grid or [10, 20, 40, 60, 120]
    radicand = es_by_horizon[base_horizon] ** 2
    for previous, current in zip(grid, grid[1:], strict=False):
        radicand += es_by_horizon[current] ** 2 * ((current - previous) / base_horizon)
    return math.sqrt(max(radicand, 0.0))


def write_liquidity_horizon_artifact(
    results: list[LiquidityHorizonESResult],
    path: Path = ARTIFACT_PATH,
) -> None:
    rows = []
    for result in results:
        for horizon, es_value in result.es_by_horizon.items():
            rows.append(
                {
                    "factor_set": result.factor_set,
                    "observation_period": result.observation_period,
                    "liquidity_horizon": horizon,
                    "base_10d_es": result.base_10d_es,
                    "horizon_es": es_value,
                    "liquidity_adjusted_es": result.liquidity_adjusted_es,
                    "q_set": "|".join(result.q_sets[horizon]),
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def result_asdict(result: LiquidityHorizonESResult) -> dict[str, Any]:
    return asdict(result)
