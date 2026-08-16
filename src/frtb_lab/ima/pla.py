"""Selected MAR32 PLA Spearman and KS mechanics."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from frtb_lab.ima.pnl import generate_daily_pnl, pla_sample
from frtb_lab.sensitivities.common import REPO_ROOT

PLA_ARTIFACT = REPO_ROOT / "data" / "artifacts" / "phase7_pla_results.csv"


@dataclass(frozen=True)
class PLAResult:
    desk_id: str
    sample_start: str
    sample_end: str
    observations: int
    spearman: float
    ks_statistic: float
    pla_zone: str
    dominant_failure_metric: str
    notes: str


def ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: (item[1], item[0]))
    output = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        end = position + 1
        while end < len(indexed) and indexed[end][1] == indexed[position][1]:
            end += 1
        average_rank = (position + 1 + end) / 2.0
        for item_index in range(position, end):
            output[indexed[item_index][0]] = average_rank
        position = end
    return output


def spearman_correlation(hpl: list[float], rtpl: list[float]) -> float:
    if len(hpl) != len(rtpl) or not hpl:
        raise ValueError("HPL and RTPL samples must have the same non-zero length.")
    return _pearson(ranks(hpl), ranks(rtpl))


def ks_statistic(hpl: list[float], rtpl: list[float]) -> float:
    if len(hpl) != len(rtpl) or not hpl:
        raise ValueError("HPL and RTPL samples must have the same non-zero length.")
    support = sorted(set(hpl) | set(rtpl))
    sample_size = len(hpl)
    max_difference = 0.0
    for value in support:
        hpl_cdf = sum(1 for item in hpl if item <= value) / sample_size
        rtpl_cdf = sum(1 for item in rtpl if item <= value) / sample_size
        max_difference = max(max_difference, abs(hpl_cdf - rtpl_cdf))
    return max_difference


def pla_zone(spearman: float, ks_value: float) -> str:
    if spearman > 0.80 and ks_value < 0.09:
        return "GREEN"
    if spearman < 0.70 or ks_value > 0.12:
        return "RED"
    return "AMBER"


def dominant_failure_metric(spearman: float, ks_value: float) -> str:
    red_spearman = spearman < 0.70
    red_ks = ks_value > 0.12
    if red_spearman and red_ks:
        return "SPEARMAN_AND_KS"
    if red_spearman:
        return "SPEARMAN"
    if red_ks:
        return "KS"
    if not (spearman > 0.80):
        return "SPEARMAN_AMBER"
    if not (ks_value < 0.09):
        return "KS_AMBER"
    return "NONE"


def calculate_pla(
    pnl_rows: list[dict[str, Any]] | None = None,
    *,
    write_artifact: bool = True,
) -> list[PLAResult]:
    rows = pnl_rows or generate_daily_pnl()
    samples = pla_sample(rows)
    results = []
    for desk_id, sample in samples.items():
        hpl = [float(row["hpl"]) for row in sample]
        rtpl = [float(row["rtpl"]) for row in sample]
        spearman = spearman_correlation(hpl, rtpl)
        ks_value = ks_statistic(hpl, rtpl)
        results.append(
            PLAResult(
                desk_id=desk_id,
                sample_start=sample[0]["date"],
                sample_end=sample[-1]["date"],
                observations=len(sample),
                spearman=spearman,
                ks_statistic=ks_value,
                pla_zone=pla_zone(spearman, ks_value),
                dominant_failure_metric=dominant_failure_metric(spearman, ks_value),
                notes="SIMULATED_PLA_DIAGNOSTIC",
            )
        )
    if write_artifact:
        write_pla_artifact(results)
    return results


def write_pla_artifact(results: list[PLAResult], path: Path = PLA_ARTIFACT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [result.__dict__ for result in results]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _pearson(left: list[float], right: list[float]) -> float:
    mean_left = sum(left) / len(left)
    mean_right = sum(right) / len(right)
    numerator = sum(
        (x - mean_left) * (y - mean_right) for x, y in zip(left, right, strict=True)
    )
    left_var = sum((x - mean_left) ** 2 for x in left)
    right_var = sum((y - mean_right) ** 2 for y in right)
    denominator = math.sqrt(left_var * right_var)
    if denominator == 0.0:
        raise ValueError("Spearman correlation is undefined for constant ranks.")
    return numerator / denominator


if __name__ == "__main__":
    calculate_pla()
