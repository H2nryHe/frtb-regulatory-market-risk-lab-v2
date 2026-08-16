# FRTB Regulatory Market Risk Capital & Validation Lab V2
## Final Validation Report

## 1. Executive Summary

This project is a source-traceable educational implementation of selected Basel
market-risk mechanics. It demonstrates how selected Standardised Approach
capital, DRC, RRAO, ES, liquidity horizons, RFET, PLA, desk backtesting, NMRF
SES and desk routing interact in a controlled synthetic portfolio.

Final project decision: RELEASE_READY_FOR_EDUCATIONAL_PORTFOLIO_USE.

The decision preserves adverse validation outcomes. Two RFET factors fail, the
original reduced set fails later RFET validation, TD-FX passes backtesting but
fails PLA, and several findings remain open.

## 2. Scope

The scope is selected Basel market-risk mechanics and validation discipline in
a reproducible Python lab. The project prioritizes source provenance,
deterministic tests, documented boundaries and clear routing consequences over
broad asset-class coverage.

## 3. What Was Built

The repository contains selected SBM, non-securitisation DRC, RRAO, IMA ES,
liquidity-horizon aggregation, stress calibration, RFET, NMRF classification,
PLA, desk backtesting, IMCC, SES, desk routing and a U.S. proposed-framework
crosswalk.

## 4. What Was Not Built

The project does not build full Basel MAR21/MAR33 coverage, securitisation DRC,
CTP, IMA default-risk model mechanics, bank-wide multiplier, amber surcharge,
final bank-wide aggregation or a U.S. proposal capital engine.

## 5. Data and Assumptions

All portfolio positions, market states, risk-factor histories, P&L vectors and
stress scenarios are deterministic synthetic fixtures. They are designed for
mechanics validation and are not institutional market evidence.

## 6. Regulatory Sources

Basel source provenance is maintained in `regulatory/source_register.yaml` and
`regulatory/parameter_crosswalk.csv`. U.S. proposal sources are recorded
separately with `retrieval_date_basis: UTC`.

Primary Basel sources: BIS MAR20, MAR21, MAR22, MAR23, MAR30, MAR31, MAR32 and
MAR33.

U.S. crosswalk sources: Federal Reserve R-1887 page, Federal Register
91 FR 14952, OCC Bulletin 2026-9 and FDIC FIL-8-2026.

## 7. Source Retrieval Dates

Basel retrieval metadata is preserved from prior phases. U.S. proposal sources
were retrieved on 2026-08-16 UTC for the final Phase 10 validation pass.

## 8. Standardised Approach Results

The selected SA scope includes GIRR, Equity and FX SBM components,
non-securitisation DRC and RRAO. It excludes full CSR SBM, commodity,
securitisation DRC and CTP.

## 5. SBM

The selected SBM implements raw and weighted sensitivities, bucket aggregation,
cross-bucket aggregation, LOW/MEDIUM/HIGH correlation scenarios and scenario
selection for selected GIRR, Equity and FX examples.

Selected-scope SBM: `601060.6801585773`.

## 6. Non-Securitisation DRC

The DRC implementation covers a selected corporate non-securitisation example
with gross JTD, LGD, maturity scaling, seniority-constrained same-obligor
netting, HBR, risk weights and bucket aggregation.

Non-securitisation DRC: `25200.0`.

## 7. RRAO

The selected RRAO classifier distinguishes vanilla options, exotic-underlying
examples and other-residual-risk examples. `SYN_EQ_BARRIER` is treated as
OTHER_RESIDUAL_RISK because it is path-dependent and has ordinary equity
underlying.

RRAO: `250.0`.

## 8. Selected-Scope SA Results

| Component | Value |
| --- | ---: |
| Selected-scope SBM | 601060.6801585773 |
| Non-securitisation DRC | 25200.0 |
| RRAO | 250.0 |
| Selected-scope SA | 626510.6801585772 |

## 9. IMA Expected Shortfall Results

Phase 5 implements selected 97.5% ES mechanics over deterministic synthetic
10-business-day shocks.

`ES_F_C`: `135310.97891484312`.

The IMA mechanics support the 10/20/40/60/120-day liquidity-horizon grid and
Q(P,j) subset aggregation. The selected stress window is 2008-07-28 to
2009-07-14.

`ES_R_C`: `136600.78255244752`.

`ES_R_S`: `377307.3028054556`.

Phase 5 reduced-set coverage ratio: `1.0116454032543514`.

## 10. RFET Results

Five selected factors are evaluated with simulated RFET mechanics:

| Factor | Result | Treatment |
| --- | --- | --- |
| RF_GIRR_USD_5Y_RATE | PASS via ROUTE_1 | ES candidate pending real-data validation |
| RF_EQUITY_SPX_SPOT | PASS via ROUTE_2 | ES candidate pending real-data validation |
| RF_EQUITY_SPX_VOL_1Y | FAIL | NMRF candidate |
| RF_FX_EURUSD_SPOT | FAIL | NMRF candidate |
| RF_FX_EURUSD_VOL_1Y | PASS via ROUTE_1 | ES candidate pending real-data validation |

Synthetic RFET observations are not institutional market evidence.

## 11. PLA and Backtesting Results

TD-RATES and TD-EQUITY are PLA GREEN and pass both selected backtests. TD-FX
passes both selected backtests but is PLA RED because its RTPL design omits
volatility and has a spot-sign mismatch.

MAR32.19 boundary correction is preserved: 99% breaches when exceptions are
greater than 12; 97.5% breaches when exceptions are 30 or more.

## 12. IMCC and SES Results

Selected modelled-factor IMCC mechanics use eligible TD-RATES and TD-EQUITY
factors, constrained risk-class ES and rho `0.5`.

Simulated selected IMCC: `358979.94225370314`.

The selected SES example uses `RF_EQUITY_SPX_VOL_1Y`, a 20-business-day
effective NMRF liquidity horizon and a selected stress period of 2019-09-19 to
2020-09-04.

Simulated selected SES: `26655.82413840059`.

## 13. Capital Routing Results

| Desk | Routing result |
| --- | --- |
| TD-RATES | SIMULATED_IMA_BRANCH |
| TD-EQUITY | SIMULATED_IMA_BRANCH |
| TD-FX | SIMULATED_SA_FALLBACK |
| TD-CREDIT | SELECTED_SA_ONLY |

NMRF status alone does not force desk fallback. TD-EQUITY remains on the
simulated IMA branch while its equity-volatility NMRF candidate goes to selected
SES mechanics.

Reduced-set failure and remediation story:

The original Phase 5 reduced set is preserved and later fails simulated RFET
validation. Phase 8 creates a separate remediated candidate set for selected
IMCC mechanics, but the original finding is not silently closed.

The project calculates selected component mechanics and routing evidence. It
does not calculate a final bank-wide aggregate because required components such
as IMA default-risk model mechanics, bank-wide multiplier, amber surcharge and
complete fallback treatment remain outside scope.

Final bank-wide aggregate: NOT_CALCULATED.

## 14. U.S. 2026 Proposal Crosswalk

Phase 9 records R-1887 as PROPOSED / NOT FINAL / CROSSWALK ONLY. The U.S.
proposal differs materially from the Basel implementation in areas including
models-based NDCR, Type A / Type B NMRF treatment, fallback capital and
applicability thresholds.

U.S. proposal parameters are isolated in
`regulatory/us_2026_proposed_parameters.csv` and are not loaded by the Basel
engine.

## 15. Findings Inventory

The final findings inventory contains seven open or pending items, including
RFET observation failures, the reduced-set conflict, synthetic evidence
limitations, TD-FX PLA RED / RTPL gap and a U.S. source interpretation note.

Open findings are acceptable because they are documented, routed and not falsely
closed.

## 16. Tests and Validation

The test suite covers parameter provenance, sensitivity units, SBM aggregation,
correlation scenarios, curvature sign, DRC JTD/HBR, RRAO classification, ES,
Q(P,j), RFET Route 1 / Route 2, 90-day coverage, PLA thresholds, backtesting
boundaries, no-lookahead checks, IMCC rho, SES aggregation, routing, U.S.
parameter isolation and release regression.

## 17. CI and Reproducibility

Release validation is available through:

```bash
python -m frtb_lab.release_validation
```

The command recomputes canonical outputs from tracked source/config inputs and
prints a concise PASS/FAIL summary without writing required artifacts.

GitHub Actions runs install, pytest, ruff and release validation across Python
3.10, 3.11 and 3.12.

## 18. Privacy and Release Packaging

Private control files remain ignored: `PROJECT_FRTB_V2_SPEC.md`,
`FRTB_V2_STATUS.md` and `local_frtb_v2_baseline/`. Generated artifacts and
local caches are excluded from the public release inventory.

## 19. Key Interview Talking Points

The project is useful to discuss source traceability, deterministic validation,
adverse finding preservation, routing consequences, U.S. proposal isolation and
the difference between selected mechanics and complete regulatory calculation.

## 20. Known Limitations

This is an educational portfolio project using synthetic data. It is not a
complete Basel implementation, not a current U.S. implementation, not a bank
filing system, and not an institutionally validated model.

No final regulatory capital, final bank-wide total, or U.S. proposal capital
number is produced.

## 21. Final Decision

RELEASE_READY_FOR_EDUCATIONAL_PORTFOLIO_USE.

This decision means the repository is ready for educational portfolio review
after user-controlled commit/publish steps. It does not mean the project is
suitable for operational use or regulatory filing.

## 22. Release Checklist

- Regression suite passes.
- Ruff lint passes.
- Release validation command passes without `PYTHONPATH`.
- U.S. status remains proposed / not final.
- Private files remain ignored and untracked.

## 23. Appendix: One-Command Validation

```bash
python -m frtb_lab.release_validation
```
