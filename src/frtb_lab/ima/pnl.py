"""Deterministic synthetic HPL, RTPL and APL series for Phase 7."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from frtb_lab.ima.synthetic_history import generate_synthetic_history, ten_day_shocks
from frtb_lab.sensitivities.common import REPO_ROOT, load_yaml

CONFIG_PATH = REPO_ROOT / "configs" / "ima" / "desk_model_specifications.yaml"
DAILY_PNL_ARTIFACT = REPO_ROOT / "data" / "artifacts" / "phase7_daily_pnl.csv"


def load_desk_model_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return load_yaml(path)


def selected_desk_ids(config: dict[str, Any] | None = None) -> tuple[str, ...]:
    cfg = config or load_desk_model_config()
    return tuple(
        desk_id
        for desk_id, desk in cfg["desk_models"].items()
        if desk["selected_phase7_scope"]
    )


def generate_daily_pnl(
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    cfg = config or load_desk_model_config()
    history = generate_synthetic_history()
    one_day_shocks = ten_day_shocks(history, window_days=1)
    rows = []
    for index, shock in enumerate(one_day_shocks):
        for desk_id in selected_desk_ids(cfg):
            desk = cfg["desk_models"][desk_id]
            hpl = _weighted_pnl(shock, desk["factor_exposures"])
            rtpl = _weighted_pnl(shock, desk["rtpl_factor_weights"])
            apl_intraday = _synthetic_intraday_component(
                hpl,
                index=index,
                scale=float(desk["apl_intraday_scale"]),
                frequency=int(desk["apl_intraday_frequency"]),
            )
            rows.append(
                {
                    "date": shock["end_date"],
                    "start_date": shock["start_date"],
                    "desk_id": desk_id,
                    "hpl": hpl,
                    "rtpl": rtpl,
                    "apl": hpl + apl_intraday,
                    "apl_label": cfg["global_rules"]["apl_label"],
                    "static_positions": cfg["global_rules"]["hpl_static_positions"],
                    "hpl_excludes_intraday_trading": cfg["global_rules"][
                        "hpl_excludes_intraday_trading"
                    ],
                    "apl_intraday_component": apl_intraday,
                    "notes": "Synthetic deterministic daily P&L; positive values are gains.",
                }
            )
    return rows


def pnl_by_desk(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["desk_id"], []).append(row)
    return grouped


def latest_n_rows(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: row["date"])[-count:]


def pla_sample(
    rows: list[dict[str, Any]],
    *,
    observations: int = 250,
) -> dict[str, list[dict[str, Any]]]:
    return {
        desk_id: latest_n_rows(desk_rows, observations)
        for desk_id, desk_rows in pnl_by_desk(rows).items()
    }


def write_daily_pnl_artifact(
    rows: list[dict[str, Any]],
    path: Path = DAILY_PNL_ARTIFACT,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _weighted_pnl(shock: dict[str, Any], weights: dict[str, float]) -> float:
    return sum(float(weight) * float(shock[factor_id]) for factor_id, weight in weights.items())


def _synthetic_intraday_component(
    hpl: float,
    *,
    index: int,
    scale: float,
    frequency: int,
) -> float:
    if frequency <= 0:
        return 0.0
    direction = -1.0 if index % (2 * frequency) == 0 else 1.0
    pulse = scale * abs(hpl) if index % frequency == 0 else 0.0
    return direction * pulse


if __name__ == "__main__":
    write_daily_pnl_artifact(generate_daily_pnl())
