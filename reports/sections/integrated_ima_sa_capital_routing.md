# Integrated IMA / SA Capital Routing Case Study

## Purpose

Phase 8 links the selected synthetic RFET, PLA/backtesting, IMCC, SES and SA
fallback mechanics into one routing case study. It demonstrates how desk routing
changes which selected components can be calculated, without producing a final
bank-wide aggregate.

## Regulatory Basis

The Phase 8 mechanics use BIS_MAR33.13-MAR33.15 for modelled-factor IMCC,
BIS_MAR33.16-MAR33.17 for selected NMRF stress-scenario and SES mechanics, and
BIS_MAR33.40 for model-ineligible desk fallback context. BIS_MAR31 and BIS_MAR32
remain the source basis for the upstream RFET and PLA/backtesting outcomes used
in routing.

## Phase 7 Regression Audit

The selected-scope SA result remains `626510.6801585772`, consisting of selected
SBM `601060.6801585773`, selected non-securitisation DRC `25200.0`, and selected
RRAO `250.0`.

The provisional IMA ES mechanics remain unchanged: `ES_F,C =
135310.97891484312`, `ES_R,C = 136600.78255244752`, and `ES_R,S =
377307.3028054556`. RFET outcomes also remain unchanged: GIRR USD 5Y rate PASS
via Route 1, equity spot PASS via Route 2, equity 1Y volatility FAIL, FX spot
FAIL, and FX 1Y volatility PASS via Route 1.

Desk diagnostics remain unchanged. TD-RATES and TD-EQUITY are GREEN/PASS
simulated IMA test-gate passes. TD-FX is PLA RED, backtesting PASS, and routes to
simulated SA fallback. TD-CREDIT remains outside the selected IMA diagnostic
scope.

## Scope and Claim Boundaries

This is a synthetic educational implementation of selected Basel mechanics. It
is not an institutional modellability determination, supervisory approval, or a
complete regulatory capital calculation.

Phase 8 uses explicit scenario assumptions because synthetic RFET observations
are not institutional real-price evidence. All outputs are labelled as selected
component mechanics or routing case-study values.

## Desk Routing

| Desk | PLA | Backtesting | Phase 8 route | Reason |
| --- | --- | --- | --- | --- |
| TD-RATES | GREEN | PASS | SIMULATED_IMA_BRANCH | Phase 7 diagnostics permit selected IMA-branch mechanics in the case study. |
| TD-EQUITY | GREEN | PASS | SIMULATED_IMA_BRANCH | Phase 7 diagnostics permit modelled-factor IMCC and selected NMRF SES mechanics. |
| TD-FX | RED | PASS | SIMULATED_SA_FALLBACK | PLA RED route is applied before eligible-desk factor aggregation. |
| TD-CREDIT | Out of selected scope | Out of selected scope | SELECTED_SA_ONLY | No PLA, RTPL, IMA DRC or credit-spread IMA model is fabricated. |

## Eligible-Desk Factor Universe

Eligible IMA-branch modelled-factor mechanics include only
`RF_GIRR_USD_5Y_RATE` and `RF_EQUITY_SPX_SPOT`. The eligible-desk NMRF set
contains only `RF_EQUITY_SPX_VOL_1Y`.

`RF_FX_EURUSD_SPOT` and `RF_FX_EURUSD_VOL_1Y` are excluded from eligible-desk
Phase 8 IMA aggregation because TD-FX is routed to selected SA fallback before
IMCC or SES aggregation.

## Original Reduced-Set Failure

The original Phase 5 reduced set is preserved in
`configs/ima/reduced_factor_set.yaml`. Phase 6 showed that two members of that
set failed simulated RFET mechanics, producing a reduced-set RFET conflict and
OPEN findings.

## Phase 8 Reduced-Set Remediation

The new candidate set is stored separately in
`configs/ima/phase8_remediated_reduced_factor_set.yaml`. It includes the two
eligible simulated modelled factors: `RF_GIRR_USD_5Y_RATE` and
`RF_EQUITY_SPX_SPOT`.

The selection is based on eligible desks, Phase 8 simulated modelled-factor
treatment, sufficient synthetic history, and a predeclared no-tuning rule. For
this selected scope, the reduced set equals the modelled full set.

## Revalidated Reduced-Set Coverage

The 12-week reduced/full diagnostic is recomputed for the Phase 8 eligible
modelled-factor universe. The average ratio is `1.0` against the sourced `0.75`
minimum, so the Phase 8 candidate reduced set passes the selected mechanics
gate.

## Modelled-Factor ES

Modelled-factor ES uses current synthetic positions, 97.5% empirical ES, direct
overlapping shocks and liquidity-horizon aggregation from the existing Phase 5
mechanics. The Phase 8 stress period is selected algorithmically for the new
eligible modelled-factor universe.

## Unconstrained ES

The unconstrained component permits empirical dependence between the eligible
interest-rate and equity modelled factors. Its selected component value is
`303550.439393035`, using the stress period from `2008-07-28` to `2009-07-14`.

## Risk-Class Constrained ES

The constrained interest-rate component holds non-interest-rate modelled factors
constant and produces `170530.01174484068`. The constrained equity component
holds non-equity modelled factors constant and produces `243879.43336953063`.
Both constrained components use the same selected stress period as the
unconstrained component.

## IMCC Mechanics

The selected MAR33.15 case-study aggregation uses `rho = 0.5`:

```text
rho * IMCC(C) + (1 - rho) * sum(IMCC(C_i))
```

The constrained sum is `414409.4451143713`, producing selected IMCC mechanics
of `358979.94225370314`. No SA fallback amount is mixed into IMCC.

## Eligible-Desk NMRF Set

The only canonical eligible-desk NMRF is `RF_EQUITY_SPX_VOL_1Y` from TD-EQUITY.
`RF_FX_EURUSD_SPOT` remains an NMRF candidate from Phase 6, but it is excluded
from eligible-desk SES because TD-FX routes to selected SA fallback.

## NMRF Stress-Scenario Method

The selected NMRF method uses deterministic synthetic historical shocks and
full revaluation of the current TD-EQUITY option exposure. The stress loss is
calculated as a 97.5% empirical expected shortfall over the selected stressed
window. The sign convention is positive loss from negative revaluation P&L.

This empirical tail convention and full-revaluation implementation are project
stress-scenario model choices, not Basel-prescribed interpolation rules.

## NMRF Liquidity Horizon

The selected equity-volatility source liquidity horizon is `20` business days.
The effective NMRF liquidity horizon is:

```text
max(source liquidity horizon, 20 days)
```

For the canonical NMRF, the effective liquidity horizon is therefore `20`
business days.

## SES Aggregation

`RF_EQUITY_SPX_VOL_1Y` is broad index volatility, so it is treated as a
remaining NMRF rather than an idiosyncratic equity zero-correlation case. The
selected stress period is `2019-09-19` to `2020-09-04`; the stress-scenario loss
and SES contribution are `26655.82413840059`. With one remaining NMRF, selected
SES mechanics are `26655.82413840059`.

## FX Desk SA Fallback

TD-FX selected SA fallback attribution uses existing selected SA mechanics where
traceable. Selected FX SBM components are delta `225542.7953442151`, vega
`38673.6331829128`, and curvature `0.0`. These are labelled
`SELECTED_SA_FALLBACK_COMPONENTS`, not complete desk-level fallback SA.

## Credit Desk SA Scope

TD-CREDIT remains selected SA-only. The traceable selected SA-side component is
non-securitisation DRC of `25200.0` for the controlled corporate bond example.
No PLA, RTPL, IMA default-risk model or credit-spread IMA model is created for
TD-CREDIT.

## Capital Routing Matrix

`governance/capital_routing_matrix.csv` traces each selected desk and factor to
IMCC, SES or selected SA fallback. The generated routing artifact also records a
whole selected SA reference as reference-only, and explicitly does not add it to
Phase 8 IMA components.

## Findings and Remediation

Existing RFET and PLA/backtesting findings are mapped in
`governance/phase8_integrated_findings.csv`. Capital treatment does not close
root-cause findings. The equity-vol insufficient-observation finding remains
OPEN, the FX spot coverage-gap finding remains OPEN, the reduced-set conflict is
marked remediation implemented pending validation, and the synthetic evidence
limitation remains OPEN.

## What Can Be Calculated

Phase 8 calculates selected modelled-factor IMCC mechanics, selected eligible
NMRF SES mechanics, selected TD-FX SA fallback components, selected TD-CREDIT
non-securitisation DRC evidence, and an integrated routing matrix.

## What Cannot Be Calculated

The project does not calculate IMA default-risk model mechanics, the MAR33.41
final aggregate, the bank-wide backtesting multiplier, PLA amber surcharge,
complete desk-level fallback SA, or any institutional approval result.

## Why No Final Total FRTB Capital Is Reported

The final MAR33 aggregation requires components deliberately outside this phase,
including most-recent versus previous-60-day averaging, multiplier mechanics,
IMA default-risk model mechanics, complete SA for model-ineligible desks, and
amber surcharge treatment where applicable.

The final aggregate is `NOT_CALCULATED`. This is deliberate scope control, not a
missing arithmetic step.

## Interview / Decision Story

The case study starts with RFET and desk diagnostics, then routes TD-RATES and
TD-EQUITY to selected IMA-branch mechanics while routing TD-FX to selected SA
fallback because PLA RED overrides its factor-level status. TD-CREDIT stays on
the selected SA side because it was never in selected IMA diagnostic scope.

That sequence is the main decision point: factor status alone is not enough.
Desk route decides whether a factor can enter eligible-desk IMCC or SES.

## Limitations

All histories, RFET observations and P&L series are synthetic. The implementation
does not use actual transaction evidence, committed quotes, vendor observations,
production desk models, institutional validation evidence, or supervisory
acceptance decisions.
