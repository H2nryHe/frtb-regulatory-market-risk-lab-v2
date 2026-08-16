# Final Validation Snapshot

Release validation date: 2026-08-16

Project decision: RELEASE_READY_FOR_EDUCATIONAL_PORTFOLIO_USE

## Implementation Scope

Source-traceable educational implementation of selected Basel market-risk
mechanics for deterministic synthetic positions and histories. The project
covers selected SBM, non-securitisation DRC, RRAO, IMA ES mechanics, liquidity
horizons, RFET, PLA/backtesting, selected IMCC/SES mechanics, desk routing, and
a U.S. 2026 proposed-framework crosswalk.

## Canonical Numerical Outputs

| Measure | Value |
| --- | ---: |
| Selected-scope SBM | 601060.6801585773 |
| Non-securitisation DRC | 25200.0 |
| RRAO | 250.0 |
| Selected-scope SA | 626510.6801585772 |
| ES_F_C | 135310.97891484312 |
| ES_R_C | 136600.78255244752 |
| ES_R_S | 377307.3028054556 |
| Phase 5 reduced-set coverage | 1.0116454032543514 |
| Simulated selected IMCC | 358979.94225370314 |
| Simulated selected SES | 26655.82413840059 |

Final bank-wide aggregate: NOT_CALCULATED.

## RFET Outcomes

| Risk factor | Result | Route / treatment |
| --- | --- | --- |
| RF_GIRR_USD_5Y_RATE | PASS | ROUTE_1 |
| RF_EQUITY_SPX_SPOT | PASS | ROUTE_2 |
| RF_EQUITY_SPX_VOL_1Y | FAIL | NMRF_CANDIDATE |
| RF_FX_EURUSD_SPOT | FAIL | NMRF_CANDIDATE |
| RF_FX_EURUSD_VOL_1Y | PASS | ROUTE_1 |

Original reduced-set audit: REDUCED_SET_RFET_MECHANICS_FAIL.

## PLA / Backtesting / Routing

| Desk | PLA | 97.5% backtest | 99% backtest | Route |
| --- | --- | --- | --- | --- |
| TD-RATES | GREEN | PASS | PASS | SIMULATED_IMA_BRANCH |
| TD-EQUITY | GREEN | PASS | PASS | SIMULATED_IMA_BRANCH |
| TD-FX | RED | PASS | PASS | SIMULATED_SA_FALLBACK |
| TD-CREDIT | OUT_OF_SELECTED_IMA_DIAGNOSTIC_SCOPE | OUT_OF_SELECTED_IMA_DIAGNOSTIC_SCOPE | OUT_OF_SELECTED_IMA_DIAGNOSTIC_SCOPE | SELECTED_SA_ONLY |

## U.S. Proposal Status

R-1887 status: PROPOSED / NOT FINAL / CROSSWALK ONLY.

Federal Register citation: 91 FR 14952, Document 2026-05959.

Retrieval date basis: UTC.

## Findings and Tests

Open or pending findings in final inventory: 7.

Current working-tree test baseline at Phase 10 packaging: 193 tests before
Phase 10 additions; final count is recorded in FRTB_V2_STATUS.md after the
acceptance run.

## Limitations

No complete seven-risk-class SBM, securitisation DRC, CTP, IMA default-risk
model, bank-wide multiplier, PLA amber surcharge, final MAR33 aggregate,
production data pipeline, or U.S. 2026 proposal calculation engine is included.
