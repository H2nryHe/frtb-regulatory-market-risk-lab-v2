# Phase 7: PLA, Backtesting and Desk Diagnostics

This section records deterministic Phase 7 diagnostics for selected synthetic
desks under BIS MAR32. It is not an institutional IMA approval assessment and it
does not calculate final IMCC, NMRF stress-scenario capital, PLA amber capital
surcharge, bank-wide backtesting zones or Phase 8 aggregation.

## Source Scope

Phase 7 uses BIS MAR32 for P&L attribution and desk-level VaR backtesting rules.
HPL is constructed from static previous-day positions with present-day market
data. RTPL is constructed from the declared risk-management-model factors for
each desk. The PLA tests use the most recent 250 observations and the Spearman
and Kolmogorov-Smirnov thresholds from MAR32. Desk-level VaR backtesting uses
one-day 97.5% and 99% VaR, calibrated to the most recent 12 months and compared
against both APL and HPL. Under MAR32.19, desk-level fallback triggers at more
than 12 exceptions for 99% VaR or at 30 or more exceptions for 97.5% VaR.

## Desk Model Specifications

Desk model specifications are frozen in
`configs/ima/desk_model_specifications.yaml` before metric evaluation.

| Desk | HPL factors | RTPL factors | NMRF candidates in desk scope | Declared challenge |
| --- | --- | --- | --- | --- |
| TD-RATES | RF_GIRR_USD_5Y_RATE | RF_GIRR_USD_5Y_RATE | none | High alignment |
| TD-EQUITY | RF_EQUITY_SPX_SPOT; RF_EQUITY_SPX_VOL_1Y | RF_EQUITY_SPX_SPOT; RF_EQUITY_SPX_VOL_1Y | RF_EQUITY_SPX_VOL_1Y | Scaled volatility proxy |
| TD-FX | RF_FX_EURUSD_SPOT; RF_FX_EURUSD_VOL_1Y | RF_FX_EURUSD_SPOT | RF_FX_EURUSD_SPOT | Omitted FX volatility and spot sign mismatch |

NMRF candidate status is reported separately and is not by itself a desk
fallback trigger in Phase 7.

## P&L Sample

The canonical sample uses synthetic business days from 2025-09-01 through
2026-08-14 for each selected desk. HPL excludes intraday trading. APL is labelled
`SYNTHETIC_APL` and equals HPL plus a deterministic intraday component. RTPL uses
only the declared RTPL risk factors for the desk.

## PLA Results

| Desk | Observations | Spearman | KS | Zone | Driver |
| --- | ---: | ---: | ---: | --- | --- |
| TD-RATES | 250 | 1.0 | 0.0 | GREEN | NONE |
| TD-EQUITY | 250 | 0.9991651706427302 | 0.02400000000000002 | GREEN | NONE |
| TD-FX | 250 | -0.9972781644506312 | 0.20800000000000002 | RED | SPEARMAN_AND_KS |

The TD-FX result is the designed challenge case. It reflects the declared RTPL
factor gap and sign mismatch rather than any NMRF capital calculation.

## Backtesting Results

| Desk | Confidence | APL exceptions | HPL exceptions | Overall exceptions | Threshold | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| TD-RATES | 97.5% | 5 | 5 | 5 | 30 | PASS |
| TD-RATES | 99.0% | 2 | 2 | 2 | 12 | PASS |
| TD-EQUITY | 97.5% | 4 | 5 | 5 | 30 | PASS |
| TD-EQUITY | 99.0% | 2 | 2 | 2 | 12 | PASS |
| TD-FX | 97.5% | 6 | 6 | 6 | 30 | PASS |
| TD-FX | 99.0% | 2 | 2 | 2 | 12 | PASS |

APL and HPL exception counts are separate. The overall exception count is the
greater of the two counts for the desk and confidence level.

## Desk-Level Diagnostic

| Desk | PLA | Backtesting | Diagnostic |
| --- | --- | --- | --- |
| TD-RATES | GREEN | PASS at 97.5% and 99% | SIMULATED_IMA_TEST_GATE_PASS |
| TD-EQUITY | GREEN | PASS at 97.5% and 99% | SIMULATED_IMA_TEST_GATE_PASS |
| TD-FX | RED | PASS at 97.5% and 99% | SIMULATED_SA_FALLBACK_REQUIRED |

The TD-FX fallback diagnostic is desk-level and simulated. It is not a final
bank-wide approval conclusion.

## Findings

Open Phase 7 findings are recorded in
`governance/pla_backtesting_findings.csv`. The open items are TD-FX PLA RED and
the associated RTPL factor gap. Phase 6 RFET findings remain open and are not
closed by Phase 7.

## Deferred Work

Deferred items include final IMCC, NMRF stress-scenario capital, actual SA
fallback capital, PLA amber surcharge calculation, bank-wide backtesting zones,
IMA default-risk model mechanics, production desk governance, real-market-data
validation and Phase 8 aggregation.
