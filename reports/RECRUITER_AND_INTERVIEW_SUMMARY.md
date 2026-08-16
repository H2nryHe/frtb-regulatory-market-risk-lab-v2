# Recruiter / Interview Summary

## 30-second summary

This is a source-traceable educational implementation of selected Basel
market-risk mechanics. It covers selected Standardised Approach capital, DRC,
RRAO, IMA Expected Shortfall, liquidity horizons, RFET/NMRF classification,
PLA/backtesting, desk-level routing, selected IMCC/SES mechanics, and a separate
crosswalk to the March 2026 U.S. proposed market-risk framework.

## What I Implemented

- Selected GIRR, Equity and FX SBM sensitivities, aggregation and correlation
  scenarios.
- Selected non-securitisation DRC and RRAO.
- Synthetic 10-day 97.5% ES with 10/20/40/60/120-day liquidity horizons.
- RFET mechanics with Route 1, Route 2 and 90-day coverage checks.
- PLA and desk VaR backtesting with deterministic GREEN and RED cases.
- Selected IMCC and NMRF SES mechanics after desk routing.
- U.S. 2026 proposed-framework crosswalk with parameter isolation.

## Most Important Quantitative Results

| Result | Value |
| --- | ---: |
| Selected-scope SA | about $626.5k |
| Selected-scope SBM | about $601.1k |
| Non-securitisation DRC | $25.2k |
| RRAO | $0.25k |
| Simulated selected IMCC mechanics | about $359.0k |
| Simulated selected SES mechanics | about $26.7k |

The SA and IMA component figures are not presented as a like-for-like capital
comparison because the project intentionally does not calculate a complete final
bank-wide aggregate.

## Three Regulatory Distinctions Worth Explaining

1. ES drives selected IMA capital mechanics, while VaR still appears in
   regulatory backtesting diagnostics.
2. Factor non-modellability and desk model eligibility are related but distinct.
   An NMRF candidate can enter SES mechanics without forcing the whole desk to
   selected SA fallback.
3. The U.S. 2026 proposal is related to Basel mechanics but has material
   proposed differences, especially NDCR mixing, Type A / Type B NMRF treatment
   and fallback capital.

## Validation Failures I Intentionally Preserved

- Two of five RFET factors fail simulated RFET mechanics.
- The original Phase 5 reduced factor set fails later RFET validation.
- Equity volatility becomes an NMRF candidate.
- FX spot becomes an NMRF candidate.
- TD-FX passes backtesting but fails PLA and routes to selected SA fallback.
- Open findings remain open where no evidence remediates the root cause.

## Example Desk-Routing Story

TD-FX is the clearest validation story. Its 97.5% and 99% VaR backtests pass,
but its PLA test is RED because the synthetic RTPL model omits volatility and
has a spot-sign mismatch. The desk therefore routes to selected SA fallback. A
backtesting pass alone is not enough.

## Basel vs U.S. 2026 Proposal

The March 2026 U.S. framework remains proposed at the release source check. The
project keeps U.S. proposal parameters in a separate register and does not load
them into the Basel engine. The crosswalk highlights U.S.-specific architecture
for models-based NDCR, NMRF Type A / Type B treatment, fallback capital and
scope thresholds.

## What I Would Build Next in a Real Institution

- Production market/vendor data integration.
- Actual transaction, quote and qualifying vendor RFET evidence.
- Full CSR and commodity scope.
- Securitisation and CTP treatment.
- IMA default-risk model mechanics.
- Operational model governance workflows.
- Regulatory reporting and disclosure production controls.
