"""Phase 5 orchestration for selected-factor IMA ES mechanics."""

from __future__ import annotations

import csv
from pathlib import Path

from frtb_lab.ima.liquidity_horizon import (
    LiquidityHorizonESResult,
    liquidity_horizon_expected_shortfall,
    write_liquidity_horizon_artifact,
)
from frtb_lab.ima.revaluation import FULL_FACTOR_IDS
from frtb_lab.ima.stress_calibration import (
    calibrate_stressed_es,
    reduced_factor_ids,
    stress_windows,
    write_stress_artifacts,
)
from frtb_lab.ima.synthetic_history import (
    current_period_shocks,
    generate_synthetic_history,
    ten_day_shocks,
)
from frtb_lab.sensitivities.common import REPO_ROOT

ES_CURRENT_ARTIFACT = REPO_ROOT / "data" / "artifacts" / "phase5_es_current.csv"


def calculate_phase5_ima_es(write_artifacts: bool = True) -> dict:
    history = generate_synthetic_history()
    shocks = ten_day_shocks(history)
    current = current_period_shocks(shocks)
    full_factors = set(FULL_FACTOR_IDS)
    reduced_factors = reduced_factor_ids()
    full_current = liquidity_horizon_expected_shortfall(
        current,
        full_factors,
        factor_set_name="FULL",
        observation_period="current",
    )
    reduced_current = liquidity_horizon_expected_shortfall(
        current,
        reduced_factors,
        factor_set_name="REDUCED",
        observation_period="current",
    )
    windows = stress_windows(shocks, reduced_factors)
    calibration = calibrate_stressed_es(current, shocks, full_factors, reduced_factors)
    output = {
        "history_observations": len(history),
        "ten_day_observations": len(shocks),
        "current_observations": len(current),
        "full_current": full_current,
        "reduced_current": reduced_current,
        "stress_windows": windows,
        "stress_calibration": calibration,
        "status": "PROVISIONAL_IMA_ES_MECHANICS",
    }
    if write_artifacts:
        write_current_es_artifact([full_current, reduced_current])
        write_liquidity_horizon_artifact([full_current, reduced_current])
        write_stress_artifacts(windows, calibration)
    return output


def write_current_es_artifact(
    results: list[LiquidityHorizonESResult],
    path: Path = ES_CURRENT_ARTIFACT,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "factor_set": result.factor_set,
            "observation_period": result.observation_period,
            "base_10d_es": result.base_10d_es,
            "liquidity_adjusted_es": result.liquidity_adjusted_es,
            "status": "PROVISIONAL_IMA_ES_MECHANICS",
            "notes": "Synthetic selected-factor IMA ES mechanics only",
        }
        for result in results
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    calculate_phase5_ima_es()
