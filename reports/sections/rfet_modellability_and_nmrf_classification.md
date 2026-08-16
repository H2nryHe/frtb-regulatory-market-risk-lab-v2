# RFET, Modellability Assessment and NMRF Classification

## Purpose

Phase 6 implements simulated RFET mechanics and factor-level treatment
classification for the five selected IMA candidate factors. It preserves the
Phase 5 ES, liquidity-horizon and stress-calibration methodology and does not
calculate NMRF stress-scenario capital.

## Regulatory Basis

The implementation is mapped to [BIS MAR31](https://www.bis.org/basel_framework/chapter/MAR/31.htm),
especially MAR31.12-MAR31.26. The selected mechanics cover representative
observation mapping, Route 1 and Route 2 RFET tests, selected RFET bucketing,
monthly monitoring, the distinction between RFET data and ES calibration data,
and qualitative principles that apply after a factor passes RFET.

## Phase 5 Regression Audit

The Phase 5 canonical calculations were rerun from tracked inputs before Phase
6 work:

| Measure | Value |
| --- | ---: |
| Selected-scope SA | 626510.6801585772 |
| `ES_F,C` | 135310.97891484312 |
| `ES_R,C` | 136600.78255244752 |
| `ES_R,S` | 377307.3028054556 |
| Raw full/reduced stress ratio | 0.9905578605517198 |
| Floored stress ratio | 1.0 |
| Provisional stressed ES | 377307.3028054556 |

The synthetic level history runs from 2007-01-02 to 2026-08-14 and contains
5119 factor observations. It produces 5109 direct overlapping 10-business-day
changes. The current-period ES window is selected by 10-day shock end date:
261 shocks ending from 2025-08-15 through 2026-08-14. The first current-period
shock starts on 2025-08-01 and ends on 2025-08-15; the final current-period
shock starts on 2026-07-31 and ends on 2026-08-14.

## Critical Distinction: Synthetic Observations vs Basel Real Prices

The project reproduces selected quantitative RFET mechanics using synthetic
observation events. It does not establish institutional Basel modellability or
represent actual transaction, quote or qualifying vendor evidence.

The official MAR31 observation concept is recorded in
`configs/ima/rfet_observation_plan.yaml` separately from the project field
`project_synthetic_observation_type = SIMULATED_RFET_OBSERVATION`.

## Candidate Risk Factors

| Factor | Broad class | Phase 5 full set | Phase 5 reduced set |
| --- | --- | --- | --- |
| `RF_GIRR_USD_5Y_RATE` | interest rate | true | true |
| `RF_EQUITY_SPX_SPOT` | equity | true | true |
| `RF_EQUITY_SPX_VOL_1Y` | equity | true | true |
| `RF_FX_EURUSD_SPOT` | fx | true | true |
| `RF_FX_EURUSD_VOL_1Y` | fx | true | false |

## Observation Registry Design

The observation plan is frozen in `configs/ima/rfet_observation_plan.yaml`.
It is deterministic, predeclared, and not conditioned on reduced-set
membership, desired Phase 5 ES output, or desired NMRF outcomes.

Canonical synthetic observation counts over the final evaluation period are:

| Factor | Synthetic observation days |
| --- | ---: |
| `RF_GIRR_USD_5Y_RATE` | 27 |
| `RF_EQUITY_SPX_SPOT` | 100 |
| `RF_EQUITY_SPX_VOL_1Y` | 12 |
| `RF_FX_EURUSD_SPOT` | 24 |
| `RF_FX_EURUSD_VOL_1Y` | 29 |

## Representativeness Mapping

Every counted observation must explicitly map from observation event to
represented project risk factor and RFET bucket. The engine rejects unknown
factors, wrong-factor mappings, non-representative observations, unverified
project-mechanics observations and wrong-bucket observations. Multiple
synthetic events on the same date count once.

## RFET Route 1

Route 1 requires at least 24 representative observation days over the current
annual window and no 90-calendar-day period in the previous 12 months with
fewer than four representative observation days. Both conditions must pass.

## 90-Day Coverage Test

Phase 6 implements the 90-day requirement as inclusive calendar-day windows,
not 63-business-day approximations. Boundary behavior is deterministic:
observations exactly on the first and last day of a 90-day window are included.

## RFET Route 2

Route 2 requires at least 100 representative observation days over the previous
12 months, with at most one counted observation per day.

## Monthly Monitoring

The final 12 monthly monitoring dates end on 2026-08-14. The monitoring history
is deterministic and records status changes explicitly. A final-date pass is
not interpreted as proof that the factor passed continuously.

## RFET Results

| Factor | Annual days | Worst 90-day count | Route 1 | Route 2 | Overall | Passing route | Failure reason |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| `RF_GIRR_USD_5Y_RATE` | 27 | 6 | PASS | FAIL | PASS | ROUTE_1 | NONE |
| `RF_EQUITY_SPX_SPOT` | 100 | 0 | FAIL | PASS | PASS | ROUTE_2 | NONE |
| `RF_EQUITY_SPX_VOL_1Y` | 12 | 2 | FAIL | FAIL | FAIL | NONE | INSUFFICIENT_ANNUAL_OBSERVATIONS |
| `RF_FX_EURUSD_SPOT` | 24 | 0 | FAIL | FAIL | FAIL | NONE | RFET_90D_COVERAGE_GAP |
| `RF_FX_EURUSD_VOL_1Y` | 29 | 6 | PASS | FAIL | PASS | ROUTE_1 | NONE |

## Qualitative Modellability Principles

`governance/modellability_principles_assessment.csv` records the qualitative
principles assessment for every selected factor across observation
representativeness, volatility understatement risk, correlation representation,
market-price representativeness, update frequency, stress-period suitability
and proxy use.

Because the evidence is synthetic, rows are deliberately marked
`PROJECT_MECHANICS_ONLY` or `NOT_INSTITUTIONALLY_VERIFIABLE`.

## Why RFET Pass Is Necessary but Not Sufficient

A simulated RFET mechanics pass only moves the project factor to
`ES_CANDIDATE_PENDING_REAL_DATA_VALIDATION`. Institutional modellability
determination remains `NOT_PERFORMED` for every factor.

## ES Candidates

| Factor | Treatment |
| --- | --- |
| `RF_GIRR_USD_5Y_RATE` | `ES_CANDIDATE_PENDING_REAL_DATA_VALIDATION` |
| `RF_EQUITY_SPX_SPOT` | `ES_CANDIDATE_PENDING_REAL_DATA_VALIDATION` |
| `RF_FX_EURUSD_VOL_1Y` | `ES_CANDIDATE_PENDING_REAL_DATA_VALIDATION` |

## NMRF Candidates

| Factor | Reason | NMRF capital status |
| --- | --- | --- |
| `RF_EQUITY_SPX_VOL_1Y` | INSUFFICIENT_ANNUAL_OBSERVATIONS | DEFERRED |
| `RF_FX_EURUSD_SPOT` | RFET_90D_COVERAGE_GAP | DEFERRED |

## Reduced-Set RFET Audit

The Phase 5 reduced set is preserved without post-hoc modification:

`RF_GIRR_USD_5Y_RATE`, `RF_EQUITY_SPX_SPOT`, `RF_EQUITY_SPX_VOL_1Y`,
`RF_FX_EURUSD_SPOT`.

Two reduced-set factors fail simulated RFET mechanics:
`RF_EQUITY_SPX_VOL_1Y` and `RF_FX_EURUSD_SPOT`. The reduced-set audit is
`REDUCED_SET_RFET_MECHANICS_FAIL`, with `REMEDIATION_REQUIRED`. No replacement
factor was substituted and the Phase 5 stressed ES remains provisional.

## Findings

`governance/rfet_findings.csv` records OPEN project findings for insufficient
observations, a 90-day coverage gap, reduced-set conflict and qualitative
data-evidence limitation. Documentation does not close these findings.

## Explicitly Deferred NMRF Capital

Phase 6 classifies NMRF candidates only. It does not implement NMRF
stress-scenario capital, SES aggregation, final IMCC, PLA, regulatory VaR
backtesting, desk eligibility, or IMA default-risk model mechanics.

## Limitations

The synthetic observation registry is useful for deterministic RFET mechanics
tests, but it is not market evidence. The outputs are not final regulatory ES,
not a final IMA aggregate and not institutional model approval evidence.
