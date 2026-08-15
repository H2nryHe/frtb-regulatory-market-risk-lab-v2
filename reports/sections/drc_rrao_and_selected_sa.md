# Default Risk, Residual Risk and Selected SA Capital

## Purpose

Phase 4 adds selected non-securitisation DRC and selected RRAO, then integrates
them with the Phase 3 selected-scope SBM result.

Educational selected implementation only. Not a regulatory-compliance or
production capital engine.

## Regulatory Basis

The DRC source is BIS_MAR22, using MAR22.1-MAR22.26 for non-securitisation
gross JTD, maturity scaling, same-obligor netting, bucket definitions, HBR,
credit-quality risk weights and no cross-bucket diversification.

The RRAO source is BIS_MAR23, using MAR23.1-MAR23.8 for additive scope,
classification, exclusions, gross-notional calculation and category weights.
MAR21 is used only to preserve the binding selected-scope SBM result from
Phase 3.

## Phase 3 Regression Audit

The Phase 3 SBM component-sum check recomputes every LOW/MEDIUM/HIGH scenario
from canonical inputs and verifies:

```text
scenario total = GIRR delta + Equity delta + FX delta + Equity vega + FX vega + Equity curvature + FX curvature
```

The canonical LOW, MEDIUM and HIGH selected-scope SBM totals tie because the
selected numerical scope contains one implemented bucket/risk-factor slice per
component. Scenario-adjusted correlations are still implemented and tested with
non-trivial fixtures; this tie is not interpreted as a Basel-wide property.

A test-only positive-curvature control produces strictly positive curvature
capital of `125.0`, proving canonical zero curvature is driven by the selected
long-option economics after delta removal rather than a sign or clipping bug.

## DRC Scope

Phase 4 implements only non-securitisation DRC. The canonical DRC position is
`SYN_CORP_BOND`, mapped to corporate obligor `SYN_CORP_A` with synthetic BBB
credit quality and senior debt seniority. Securitisation DRC, CTP, tranche
treatment and index decomposition remain outside scope.

## Gross Jump-to-Default

For the canonical corporate bond:

| Field | Value |
| --- | ---: |
| Face / bond-equivalent notional | 600000.0 |
| Market value | 570000.0 |
| Cumulative P&L | -30000.0 |
| LGD | 0.75 |
| Gross JTD | 420000.0 |

Gross JTD includes the P&L adjustment:

```text
0.75 * 600000 - 30000 = 420000
```

## Maturity Scaling

The canonical bond has remaining maturity `3.0` years, so the maturity scale is
`1.0` and scaled JTD remains `420000.0`. Tests cover 2Y, 6M and 1M examples;
the 1M case uses the three-month floor of `0.25`.

## Same-Obligor Netting

Same-obligor offsetting is applied after gross JTD and maturity scaling. The
seniority rule permits a short exposure to offset a long exposure only when the
short has the same or lower seniority relative to the long.

In the DRC case fixture, `SYN_OBLIGOR_A` recognises `180000.0` of permitted
offset. `SYN_OBLIGOR_B` rejects a `70000.0` attempted short senior-debt offset
against long equity/non-senior exposure.

## Seniority Rules

The selected seniority order is:

```text
equity_or_non_senior_debt < senior_debt < covered_bond
```

This supports the MAR22 example where a short equity exposure may offset a long
bond exposure, but a short bond exposure may not offset a long equity exposure.

## Net JTD

Canonical net JTD:

| Obligor | Net long JTD | Net short JTD | Status |
| --- | ---: | ---: | --- |
| SYN_CORP_A | 420000.0 | 0.0 | NO_OFFSET |

The DRC case fixture has four obligors and preserves net long and net short JTD
separately after permitted same-obligor offsetting.

## Credit Quality Risk Weights

The implemented MAR22 Table 2 selected categories are AAA, AA, A, BBB, BB, B,
CCC, Unrated and Defaulted. The canonical corporate bond uses BBB at `0.06`.
Invalid labels fail loudly rather than mapping to Unrated.

## Hedge Benefit Ratio

HBR is calculated from unweighted net JTD amounts:

```text
net_long_jtd / (net_long_jtd + abs(net_short_jtd))
```

For the canonical long-only bucket, HBR is `1.0`. For the DRC case fixture,
net long JTD is `1002500.0`, net short JTD is `-175000.0`, and HBR is
`0.851380042462845`.

## Non-Securitisation DRC Results

Canonical DRC:

| Instrument | Obligor | Seniority | Credit quality | Gross JTD | Scaled JTD | Risk weight | HBR | DRC |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| SYN_CORP_BOND | SYN_CORP_A | senior_debt | BBB | 420000.0 | 420000.0 | 0.06 | 1.0 | 25200.0 |

DRC validation fixture:

| Measure | Value |
| --- | ---: |
| Synthetic positions | 6 |
| Obligors | 4 |
| Permitted same-obligor offset | 180000.0 |
| Rejected seniority offset | 70000.0 |
| Net long JTD | 1002500.0 |
| Net short JTD | -175000.0 |
| HBR | 0.851380042462845 |
| Independently calculated DRC | 32192.03821656051 |
| Engine DRC | 32192.03821656051 |

## RRAO Classification

`SYN_EQ_BARRIER` remains primary risk class `EQUITY` and remains otherwise
eligible for future SBM treatment, but its selected numerical SBM sensitivities
remain deferred. RRAO is additive and does not remove SBM or DRC scope.

## Barrier Option: Other Residual Risk vs Exotic Underlying

The barrier option is path-dependent and therefore classified as
`OTHER_RESIDUAL_RISK` for selected RRAO. Its underlying is ordinary equity, so
it is not classified as `EXOTIC_UNDERLYING`.

This distinction drives the risk weight: `OTHER_RESIDUAL_RISK` uses `0.001`,
while `EXOTIC_UNDERLYING` uses `0.01`.

## RRAO Results

Canonical RRAO:

| Instrument | Category | Gross notional | Risk weight | Included | Contribution |
| --- | --- | ---: | ---: | --- | ---: |
| SYN_EQ_CALL | NOT_IN_SCOPE | 500000.0 | 0.0 | false | 0.0 |
| SYN_EURUSD_CALL | NOT_IN_SCOPE | 750000.0 | 0.0 | false | 0.0 |
| SYN_EQ_BARRIER | OTHER_RESIDUAL_RISK | 250000.0 | 0.001 | true | 250.0 |

The test-only `SYN_EXOTIC_UNDERLYING_NOTE` exercises the separate exotic
underlying branch and contributes `10000.0` on gross notional `1000000.0`.
Listed/CCP eligibility excludes the other-residual-risk control but does not
exclude the exotic-underlying control. Exact back-to-back control trades are
excluded.

## Selected-Scope Standardised Approach Integration

| Component | Capital |
| --- | ---: |
| Binding selected-scope SBM | 601060.6801585773 |
| Non-securitisation DRC | 25200.0 |
| RRAO | 250.0 |
| Selected-scope SA total | 626510.6801585772 |

The integration uses the binding/max Phase 3 SBM result once. It does not add
LOW, MEDIUM and HIGH SBM scenarios together.

## Capital Attribution

| Component | Capital | Contribution |
| --- | ---: | ---: |
| SBM | 601060.6801585773 | 95.938% |
| Non-securitisation DRC | 25200.0 | 4.022% |
| RRAO | 250.0 | 0.040% |

The canonical DRC is driven entirely by `SYN_CORP_A` BBB senior debt. The DRC
case fixture demonstrates that same-obligor offsetting is constrained by
seniority and that HBR is partial hedge recognition, not complete hedge
recognition. Barrier RRAO uses `0.1%` because it is other residual risk, not an
exotic-underlying instrument.

## Independent Validation Cases

Tests cover Phase 3 decomposition, scenario tie documentation, positive
curvature control, DRC long/short default-loss direction, gross JTD hand
calculation, P&L adjustment, LGD values, maturity scaling and floor,
same-obligor offsetting, rejected seniority offset, different-obligor no
netting, HBR edge cases, bucket DRC hand calculation, no cross-bucket DRC
diversification, RRAO category separation, RRAO exclusions, gross-notional
treatment, additive RRAO scope, and selected-scope SA integration.

## Explicit Omissions

Securitisation DRC, CTP, nth-to-default, tranche capital, securitisation
decomposition, complete seven-risk-class SBM, complete CSR sensitivity capital,
barrier SBM sensitivity calculation, IMA ES, RFET, PLA and backtesting are not
implemented in Phase 4.

## Limitations

The selected-scope SA result is a bounded educational result for deterministic
synthetic fixtures. It is not a filing measure, not a complete Standardised
Approach implementation, and not suitable for production use.
