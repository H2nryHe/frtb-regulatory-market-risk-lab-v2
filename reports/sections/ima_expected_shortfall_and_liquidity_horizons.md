# IMA Expected Shortfall and Liquidity Horizons

Phase 5 implements **PROVISIONAL IMA ES MECHANICS** for a selected synthetic
factor set. The outputs are diagnostic mechanics only. They are not final IMA
capital, do not establish modellability, and do not include desk eligibility,
PLA, backtesting, RFET, NMRF capital, default-risk IMA, or final IMCC
aggregation.

## Source Basis

The mechanics are mapped to [BIS MAR33](https://www.bis.org/basel_framework/chapter/MAR/33.htm).
The selected implementation covers the 97.5% ES confidence level, a 10-day base
horizon, overlapping 10-day observations, selected liquidity horizons from the
10/20/40/60/120 business-day grid, reduced-set stress calibration, and the
12-month current and stress windows needed for the Phase 5 lab scope.

Project choices are explicitly separated from BIS parameters in
`regulatory/parameter_crosswalk.csv`. Those choices include the deterministic
synthetic seed, overlapping observation convention, and finite-sample empirical
tail convention.

## Synthetic History

The synthetic history is generated from `configs/ima/synthetic_history.yaml` and
starts on 2007-01-02. It is deterministic under seed `3305` and ends on
2026-08-14. The generated series contains 5119 business-day observations and
5109 overlapping direct 10-business-day shocks.

The history is intentionally synthetic. No live vendor feed, file download, or
current market data source is used.

## Candidate Factors

The selected full factor set is:

| Factor | Selected liquidity horizon | Status |
| --- | ---: | --- |
| `RF_GIRR_USD_5Y_RATE` | 10 days | `PENDING_RFET` |
| `RF_EQUITY_SPX_SPOT` | 10 days | `PENDING_RFET` |
| `RF_EQUITY_SPX_VOL_1Y` | 20 days | `PENDING_RFET` |
| `RF_FX_EURUSD_SPOT` | 10 days | `PENDING_RFET` |
| `RF_FX_EURUSD_VOL_1Y` | 40 days | `PENDING_RFET` |

The provisional reduced set excludes `RF_FX_EURUSD_VOL_1Y` and remains marked
`PENDING_RFET_VALIDATION`. This is only a Phase 5 mechanics selection.

## Current ES

The current period is fixed at 2025-08-15 to 2026-08-14 and contains 261
overlapping 10-day observations.

| Factor set | Base 10-day ES | Liquidity-adjusted ES |
| --- | ---: | ---: |
| Full selected set | 134896.55796388566 | 135310.97891484312 |
| Provisional reduced set | 136563.38461801698 | 136600.78255244752 |

P&L is produced by selected-position revaluation and uses the convention that
negative P&L is loss. Empirical ES averages the worst `ceil(n * 2.5%)` losses.

## Liquidity Horizons

`Q(P,j)` is implemented as a nested subset of factors whose selected liquidity
horizon is at least the horizon `j`. For the full selected factor set:

| Horizon | `Q(P,j)` |
| ---: | --- |
| 10 | `RF_EQUITY_SPX_SPOT`, `RF_EQUITY_SPX_VOL_1Y`, `RF_FX_EURUSD_SPOT`, `RF_FX_EURUSD_VOL_1Y`, `RF_GIRR_USD_5Y_RATE` |
| 20 | `RF_EQUITY_SPX_VOL_1Y`, `RF_FX_EURUSD_VOL_1Y` |
| 40 | `RF_FX_EURUSD_VOL_1Y` |
| 60 | empty |
| 120 | empty |

The liquidity-horizon result uses the MAR33 selected-factor square-root
aggregation over horizon increments. It does not scale individual one-day P&L
by square root of time.

## Stress Calibration

The stress search uses rolling 252-observation windows stepped every 21
observations across the synthetic history. The selected stress window is the
window with the highest provisional reduced-set liquidity-adjusted ES:

| Metric | Value |
| --- | ---: |
| Candidate windows | 232 |
| Stress period start | 2008-07-28 |
| Stress period end | 2009-07-14 |
| `ES_F,C` | 135310.97891484312 |
| `ES_R,C` | 136600.78255244752 |
| `ES_R,S` | 377307.3028054556 |
| Raw scaling ratio | 0.9905578605517198 |
| Floored scaling ratio | 1.0 |
| Scaled stressed ES | 377307.3028054556 |

The reduced-set coverage diagnostic uses the latest 12 weekly windows and
produces an average reduced/full ES ratio of `1.0116454032543514` against a
minimum configured threshold of `0.75`, resulting in `PASS`.

## Deferred Work

Phase 5 deliberately stops before RFET, modellability classification beyond
`PENDING_RFET`, NMRF stressed expected-shortfall capital, PLA, backtesting, desk
eligibility, final IMCC aggregation, MAR33.15 rho weighting, and IMA default
risk model mechanics.
