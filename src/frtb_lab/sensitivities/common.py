"""Shared loaders and conventions for selected regulatory sensitivities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
MARKET_STATE_PATH = REPO_ROOT / "data" / "fixtures" / "canonical_market_state.yaml"
PARAMETERS_PATH = REPO_ROOT / "configs" / "sa" / "selected_sbm_parameters.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return yaml.safe_load(handle)


def load_market_state(path: Path = MARKET_STATE_PATH) -> dict[str, Any]:
    return load_yaml(path)


def load_parameters(path: Path = PARAMETERS_PATH) -> dict[str, Any]:
    return load_yaml(path)


def tenor_label(years: float) -> str:
    if years == int(years):
        return f"{int(years)}Y"
    return f"{years:g}Y"


def years_from_label(label: str) -> float:
    return float(label.removesuffix("Y"))
