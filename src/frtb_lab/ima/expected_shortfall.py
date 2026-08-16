"""Empirical 97.5% Expected Shortfall with positive-loss convention."""

from __future__ import annotations

import math


def empirical_expected_shortfall(
    pnl: list[float],
    *,
    confidence_level: float = 0.975,
    min_observations: int = 40,
) -> float:
    if len(pnl) < min_observations:
        raise ValueError(f"Expected at least {min_observations} observations, got {len(pnl)}.")
    tail_fraction = 1.0 - confidence_level
    tail_count = max(1, math.ceil(len(pnl) * tail_fraction))
    losses = sorted((-float(value) for value in pnl), reverse=True)
    return sum(losses[:tail_count]) / tail_count
