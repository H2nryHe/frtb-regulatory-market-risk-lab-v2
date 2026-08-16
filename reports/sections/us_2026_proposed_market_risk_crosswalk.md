# U.S. 2026 Proposed Market Risk Framework Crosswalk

## Purpose

Phase 9 maps the selected Basel market-risk mechanics implemented in Phases 0-8
to the March 2026 U.S. proposed market-risk framework. It is regulatory
analysis and gap analysis only.

As of the Phase 9 source retrieval date, R-1887 is analyzed as proposed
rulemaking, not as a final U.S. capital rule.

## Current Rulemaking Status

R-1887 remains classified by the Federal Reserve as a Rulemaking Proposal. The
Federal Register publication is 91 FR 14952, Document 2026-05959, published
2026-03-27, with comments due 2026-06-18. Phase 9 found no official final rule,
withdrawal, or supplemental replacement.

## Sources

Official sources are recorded in `regulatory/source_register.yaml`:

| Source | Role |
| --- | --- |
| US_R1887_FED | Federal Reserve proposal status |
| US_R1887_FEDERAL_REGISTER | Primary proposal text and proposed regulatory text |
| US_R1887_OCC | OCC bulletin corroborating proposal status and applicability summary |
| US_R1887_FDIC | FDIC FIL corroborating proposal status and optional adoption |

No consulting, law-firm, blog, news or unofficial summaries are used for Phase 9
regulatory differences.

## Critical Claim Boundary

The calculation engine remains Basel-based. Phase 9 does not replace Basel
parameters with U.S. proposal parameters, does not calculate a U.S. portfolio
capital number, and does not treat the proposal as a final rule.

## U.S. Proposed Applicability

The proposed market-risk requirements apply to a banking organization that meets
one or more proposed §__.201(b)(1) standards:

| Criterion | Proposed threshold / category | Source |
| --- | --- | --- |
| Category I / II | Depository institution holding company that is Category I or Category II | US_R1887_FEDERAL_REGISTER §__.201(b)(1)(i) |
| Significant trading activity percent test | Trading assets plus trading liabilities equal to 10 percent or more of quarter-end total assets | US_R1887_FEDERAL_REGISTER §__.201(b)(1)(ii)(A) |
| Significant trading activity dollar test | Trading assets plus trading liabilities of $5 billion or more on average for the four most recent quarters | US_R1887_FEDERAL_REGISTER §__.201(b)(1)(ii)(B) |
| Optional adoption | Other banking organizations may elect the proposed approach | US_R1887_OCC summary; US_R1887_FDIC summary |

The project has no real banking organization balance sheet and therefore does
not implement applicability determination.

## Proposed Market-Risk Architecture

```text
Standardized measure
  standardized non-default capital requirement
    = sensitivities-based capital requirement + residual risk add-on
  + default risk capital requirement
  + fallback capital requirement
  + capital add-ons for redesignations

Models-based measure
  NDCR = IMA_G,A + (SA_all_desks - SA_G,A)
  + default risk capital requirement
  + fallback capital requirement
  + capital add-ons for redesignations
```

This is materially different from simply adding whole-portfolio SA to selected
IMA components. That approach would double count model-eligible non-default
risk.

## Standardized Non-Default Capital

The U.S. proposed standardized non-default capital requirement consists of the
sensitivities-based capital requirement and residual risk add-on. DRC is
separate in the proposed standardized measure. The project Phase 4 selected SA
total includes selected SBM, non-securitisation DRC and RRAO, so it must not be
renamed as U.S. standardized non-default capital.

## Sensitivities-Based Method

The project implements selected Basel SBM mechanics for GIRR, Equity and FX:
delta, vega, curvature and LOW/MEDIUM/HIGH correlation scenarios. The U.S.
proposal contains a full proposed sensitivities-based framework across market
risk covered positions. The concepts are broadly aligned, but the U.S. proposal
is not the source of the project's numerical configs.

## Residual Risk Add-On

The U.S. proposal applies 1 percent to positions with exotic exposure and
0.1 percent to other positions with residual risks, then sums across subject
positions. It also proposes specific listed, CCP-eligible, back-to-back,
deliverable-hedge, U.S. government/GSE, fallback and internal-transaction
exclusions.

`SYN_EQ_BARRIER` is independently crosswalked: the Basel project classifies it
as other residual risk because it is path-dependent and has ordinary equity
underlying. Under the U.S. proposal, barrier and embedded-option features would
require the §__.211 inclusion and exclusion analysis. No U.S. RRAO amount is
calculated.

## Default Risk Capital

The project implements selected Basel non-securitisation DRC only. The U.S.
proposal uses a default risk capital requirement in both standardized and
models-based measures and requires a single DRC calculation across
model-eligible and model-ineligible positions for the models-based measure. The
project does not implement securitization, CTP, complete U.S. DRC, or an IMA
default-risk model.

## Models-Based Non-Default Capital

The U.S. proposed NDCR equals `IMA_G,A + (SA_all_desks - SA_G,A)`, with a
supervisory-approval alternative allowing NDCR to equal `SA_all_desks`. Phase 8
implements selected Basel IMCC/SES mechanics and selected routing, but it does
not calculate `SA_all_desks`, `SA_G,A`, or U.S. NDCR.

Phase 8 is conceptually related but not numerically equivalent.

## Expected Shortfall and IMCC

Both Basel MAR33 and the U.S. proposal use 97.5 percent ES concepts, liquidity
horizons and stress calibration. The Phase 5/8 implementation remains a selected
Basel educational engine with synthetic data. A future U.S. implementation
would need a separate proposed-rule parameter and approval layer.

## NMRF: Basel vs U.S. Type A / Type B

The U.S. proposal introduces Type A and Type B non-modellable risk factors for
SES aggregation. Proposed §__.215(d)(2) defines SES formula terms for Type A
`SES_NM,k` and Type B `SES_NM,j`, with `r_b = 0.36` for Type B aggregation.

Phase 8 uses Basel MAR33.17 selected SES mechanics and rho `0.6`; it does not
classify Type A or Type B. The separate file `regulatory/us_nmrf_crosswalk.csv`
records this gap.

## RFET / Risk-Factor Eligibility

The U.S. proposal uses risk-factor qualitative and quantitative tests. The
quantitative test requires real price observations mapped to risk-factor
buckets, no more than one counted observation per day, and third-party provider
identifier/audit controls where applicable. Proposed regulatory text specifies
24 observations for 10- or 20-day liquidity horizons and 16 otherwise.

This is not Basel RFET Route 1 / Route 2 as implemented in Phase 6. Synthetic
RFET observations remain project mechanics only.

## PLA

The U.S. proposal compares 250 business days of HPL and RTPL at trading-desk
level and uses KS-based metrics in proposed §__.213(c). The project Phase 7 PLA
implementation is broadly aligned in concept, but it remains a Basel MAR32
diagnostic and is not a U.S. supervisory desk determination.

## Desk-Level Backtesting

The proposed U.S. desk backtesting text uses APL and HPL exception counts at
99.0 percent and 97.5 percent over the most recent 250 business days. Proposed
§__.213(b)(3) makes a desk model-ineligible when it exceeds the 99.0 percent
threshold or reaches the 97.5 percent threshold as stated in the proposal. It
also includes re-eligibility and short-history proration provisions.

Phase 7 remains frozen to the selected Basel MAR32 interpretation:
99 percent `>12` and 97.5 percent `>=30`.

## Model-Eligible / Model-Ineligible Routing

The project uses `SIMULATED_IMA_TEST_GATE_PASS`,
`SIMULATED_PLA_AMBER`, and `SIMULATED_SA_FALLBACK_REQUIRED` diagnostic labels.
Those labels are not supervisory determinations. The U.S. proposal requires
agency approval and uses model-eligible / model-ineligible desk concepts in
the proposed NDCR architecture.

## Fallback Capital Requirement

Two terms are intentionally separate:

| Concept | Meaning |
| --- | --- |
| Model-ineligible desk standardized treatment | A desk or position cannot use the models-based non-default method and enters the standardized contribution in NDCR |
| Fallback capital requirement | A separate charge for positions where required calculations cannot be performed |

The proposed fallback capital requirement generally equals the sum of absolute
fair values for affected positions unless an approved alternative is used. The
project does not implement this concept.

## Basel-to-U.S. Parameter Differences

U.S. proposal parameters are stored only in
`regulatory/us_2026_proposed_parameters.csv`, with implementation status
`CROSSWALK_ONLY`. They are not added to `configs/sa/` or `configs/ima/`.

## Project Implementation Gap Matrix

`regulatory/us_project_gap_matrix.csv` records high-priority gaps for U.S. NDCR,
Type A / Type B NMRF, NMRF aggregation, desk backtesting, fallback capital,
applicability and final measure architecture.

## What the Existing Project Already Demonstrates

The project demonstrates source-traceable selected Basel mechanics: GIRR,
Equity and FX SBM; selected non-securitisation DRC; selected RRAO; selected ES
and liquidity-horizon mechanics; simulated RFET; PLA; desk VaR backtesting;
selected IMCC/SES; and component routing discipline.

## What Would Need to Change for a U.S.-Proposal Implementation

A U.S.-proposal implementation would need separate U.S. scope determination,
full standardized non-default capital, complete DRC, proposed NDCR mixing,
Type A / Type B NMRF classification, U.S. SES aggregation, proposed RF
qualitative/quantitative tests, fallback capital, redesignation add-ons and
reporting/disclosure support.

## Why No U.S. Capital Number Is Produced

Producing a U.S. number from the current selected Basel engine would create a
misleading pseudo-compliance result. The project lacks required U.S.-specific
mechanics and intentionally avoids a portfolio U.S. total.

## Key U.S. Proposal Differences to Explain in an Interview

1. The proposed models-based NDCR uses `IMA_G,A + (SA_all_desks - SA_G,A)`, not
   partial IMA plus whole-portfolio SA.
2. The proposal introduces Type A and Type B NMRF treatment; the Basel project
   has no Type A / Type B classifier.
3. Proposed Type B NMRF aggregation uses `r_b = 0.36`, separate from the
   project's Basel SES rho `0.6`.
4. The proposed fallback capital requirement is different from a
   model-ineligible desk using standardized treatment.
5. U.S. applicability is category- and trading-activity-threshold based, while
   the project is a synthetic Basel mechanics lab.

## Limitations

Phase 9 does not interpret legal ambiguity, determine bank applicability,
perform agency approval analysis, or calculate U.S. proposed capital. The
source interpretation note records the real-price observation count ambiguity
between supplementary discussion and proposed regulatory text.
