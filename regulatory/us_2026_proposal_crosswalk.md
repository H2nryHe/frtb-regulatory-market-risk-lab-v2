# U.S. 2026 Proposed Market Risk Framework Crosswalk

Phase 9 compares selected Basel mechanics implemented in Phases 0-8 with the
March 2026 U.S. proposed revised market-risk capital framework. The U.S.
proposal is analyzed as proposed rulemaking, not as a final U.S. capital rule.

Allowed alignment statuses used below: ALIGNED, BROADLY_ALIGNED,
MODIFIED_IN_US_PROPOSAL, US_SPECIFIC, BASEL_ONLY_IN_CURRENT_PROJECT,
OUT_OF_PROJECT_SCOPE, REQUIRES_FUTURE_REASSESSMENT.

| topic | Basel source | Basel treatment | project implementation | U.S. proposed source | U.S. proposed treatment | alignment status | material difference | implementation consequence | project action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. Market-risk scope / applicability | BIS_MAR20 | Basel SA scope framework and trading-book context | Synthetic portfolio only; no bank applicability test | US_R1887_FEDERAL_REGISTER §__.201(b)(1); US_R1887_OCC highlights | Category I and II depository institution holding companies plus banking organizations with significant trading activity | US_SPECIFIC | U.S. scope is institution-level and threshold-based | Existing lab cannot be described as a U.S. covered-institution implementation | Record thresholds only |
| B. Trading-book / covered-position scope | BIS_MAR20; BIS_MAR21 | Trading book and market-risk covered concepts by Basel chapter | Synthetic instruments explicitly mapped to desks and selected risk classes | US_R1887_FEDERAL_REGISTER §§__.202-__.203 | Uses U.S. market risk covered position terminology | MODIFIED_IN_US_PROPOSAL | Terminology and legal scope differ | No automatic Basel-to-U.S. scope conversion | Crosswalk only |
| C. Trading desk concept | BIS_MAR30; BIS_MAR32; BIS_MAR33 | Desk-level IMA diagnostics and model-ineligible context | TD-RATES, TD-EQUITY, TD-FX and TD-CREDIT synthetic desks | US_R1887_FEDERAL_REGISTER §§__.212-__.213 | Model-eligible and model-ineligible trading desks require supervisor approval and tests | BROADLY_ALIGNED | Project diagnostics are not supervisory determinations | Preserve simulated labels | No code change |
| D. Standardised / standardized non-default capital | BIS_MAR20-MAR23 | SA includes SBM, DRC and RRAO in Basel structure | Selected SA total = selected SBM + non-securitisation DRC + RRAO | US_R1887_FEDERAL_REGISTER Section V.A.7; §__.204(b) | Standardized non-default capital = SBM + RRAO; DRC is a separate measure component | MODIFIED_IN_US_PROPOSAL | Project Phase 4 SA total must not be renamed U.S. standardized non-default capital | Documentation must separate DRC from SNCR | Add U.S. architecture |
| E. Sensitivities-based method | BIS_MAR21 | Delta, vega and curvature across risk classes | Selected GIRR, Equity and FX only | US_R1887_FEDERAL_REGISTER §§__.206-__.209 | Sensitivities-based capital requirement for market risk covered positions | BROADLY_ALIGNED | U.S. proposal includes full U.S. regulatory text, more risk classes and approvals | Existing SBM remains selected Basel mechanics | Crosswalk only |
| F. Delta | BIS_MAR21 | Prescribed delta sensitivities and risk weights | GIRR 5Y PV01, equity spot, FX spot | US_R1887_FEDERAL_REGISTER §__.207(b) | Proposed delta definitions include interest-rate, credit-spread, equity, commodity and FX risk | BROADLY_ALIGNED | Project omits CSR delta and commodities | No U.S. delta engine | Record gap |
| G. Vega | BIS_MAR21 | Regulatory vega = model vega times volatility | Selected equity and FX option vega | US_R1887_FEDERAL_REGISTER §__.207(c) | Proposed vega sensitivity uses vega times volatility and mapping rules | BROADLY_ALIGNED | U.S. mapping for barrier/multi-strike options requires full model context | Existing selected vega remains Basel-based | No code change |
| H. Curvature | BIS_MAR21 | Full revaluation with delta removal | Selected vanilla equity and FX curvature only | US_R1887_FEDERAL_REGISTER §__.207(a), §__.207(d) and §__.208 | Proposed curvature scenarios and risk-factor definitions | BROADLY_ALIGNED | U.S. proposal contains full product and risk class scope | Barrier curvature still not invented | Crosswalk only |
| I. Low / medium / high correlation scenarios | BIS_MAR21 | Scenario max across correlation transforms | Implemented selected LOW/MEDIUM/HIGH scenario mechanics | US_R1887_FEDERAL_REGISTER Section V.A.7 and §__.209 | Three correlation scenarios with high, medium and low correlations; largest result selected | BROADLY_ALIGNED | U.S. proposed full parameter universe is not the project config | U.S. correlations are not loaded | Parameter separation |
| J. Residual risk add-on | BIS_MAR23 | Exotic underlying and other residual risk add-on | SYN_EQ_BARRIER classified OTHER_RESIDUAL_RISK under Basel MAR23 | US_R1887_FEDERAL_REGISTER Section V.A.7.i; §__.211 | Exotic exposure and other residual-risk positions with exclusions and supervisor determinations | MODIFIED_IN_US_PROPOSAL | Terminology shifts from exotic underlying to exotic exposure; U.S. exclusions and supervisor discretion are explicit | Barrier example requires independent U.S. classification | Document instrument crosswalk |
| K. Default risk capital | BIS_MAR22 | Non-securitisation DRC with JTD, LGD, maturity, netting, HBR, buckets | Selected corporate non-securitisation DRC only | US_R1887_FEDERAL_REGISTER §__.210 | Default risk capital applies under both standardized and models-based measures | BROADLY_ALIGNED | U.S. proposal includes securitizations, CTP and all covered positions | Project DRC remains selected non-securitisation only | Record gap |
| L. Models-based non-default capital | BIS_MAR33 | IMCC and SES concepts under Basel IMA | Phase 8 selected IMCC and SES mechanics; no final aggregate | US_R1887_FEDERAL_REGISTER §__.204(c); §__.215 | Models-based measure uses NDCR plus DRC, fallback and redesignation add-ons | MODIFIED_IN_US_PROPOSAL | U.S. NDCR integrates IMA_G,A with marginal standardized contribution | Phase 8 is conceptually related but not numerically equivalent | Do not calculate U.S. NDCR |
| M. Expected shortfall | BIS_MAR33 | 97.5% ES, liquidity horizons and stress calibration | Phase 5 selected ES; Phase 8 modelled-factor ES | US_R1887_FEDERAL_REGISTER §__.215(b) | ES-based measure replaces VaR-based models and uses liquidity horizons | BROADLY_ALIGNED | U.S. text is independently proposed, not Basel source for code | No U.S. ES engine | Crosswalk only |
| N. Liquidity horizons | BIS_MAR33.12 | 10/20/40/60/120 day grid for selected risk factors | Configured selected liquidity horizons | US_R1887_FEDERAL_REGISTER §__.215(b) | Proposed ES and NMRF mechanics use assigned liquidity horizons | BROADLY_ALIGNED | U.S. assignment details need complete U.S. factor universe | No config contamination | Separate U.S. parameter register |
| O. Stress calibration | BIS_MAR33 | Current/stress reduced-set calibration | Synthetic stress windows; no production data | US_R1887_FEDERAL_REGISTER §__.215(b)-(d) | Proposed models-based capital uses ES and stressed expected shortfall mechanics | BROADLY_ALIGNED | U.S. stress calibration must satisfy proposed data and approval requirements | Existing synthetic workflow is educational | Report limitation |
| P. Reduced risk-factor set | BIS_MAR33.9 | Reduced set must explain minimum average ratio | Phase 5 reduced set preserved; Phase 8 separate remediated set | US_R1887_FEDERAL_REGISTER §__.215(b) | Proposed ES measure uses internal-model factor eligibility and data controls | MODIFIED_IN_US_PROPOSAL | U.S. proposal adds RF qualitative/quantitative tests and approval context | No U.S. reduced-set proof | Gap item |
| Q. Risk-factor eligibility / modellability | BIS_MAR31 | RFET Route 1 / Route 2 plus qualitative principles | Simulated RFET mechanics only | US_R1887_FEDERAL_REGISTER §__.214(b)(2)-(3) | Risk-factor qualitative and quantitative tests, real-price mapping and third-party data controls | MODIFIED_IN_US_PROPOSAL | U.S. quantitative test is not Basel Route 1 / Route 2 | Basel RFET pass/fail does not map one-for-one | Crosswalk only |
| R. Real-price / observation requirements | BIS_MAR31 | Actual transactions, committed quotes, vendor observations and representativeness | Synthetic observation registry labelled not market evidence | US_R1887_FEDERAL_REGISTER §__.214(b)(3)(i) | Real price representative test, once-per-day count, third-party provider identifiers and audit requirements | MODIFIED_IN_US_PROPOSAL | U.S. proposal has detailed third-party provider requirements | Synthetic evidence cannot satisfy it | Report gap |
| S. NMRF treatment | BIS_MAR31; BIS_MAR33 | NMRF candidates and SES capital treatment | Phase 8 selected Basel-style SES for one equity-vol NMRF | US_R1887_FEDERAL_REGISTER §__.215(d) | Type A and Type B NMRFs enter proposed SES formula | MODIFIED_IN_US_PROPOSAL | Type A / Type B taxonomy and rb = 0.36 differ from Basel selected SES | Existing SES is not U.S. SES | Separate NMRF CSV |
| T. PLA | BIS_MAR32 | HPL vs RTPL, Spearman, KS and zones | TD-RATES/EQUITY GREEN, TD-FX RED | US_R1887_FEDERAL_REGISTER §__.213(c) | Proposed PLA compares 250 HPL and RTPL observations with KS and zone rules | BROADLY_ALIGNED | U.S. timing/approval text and transition language are proposal-specific | Phase 7 PLA remains Basel-based | Crosswalk only |
| U. Desk-level backtesting | BIS_MAR32 | 97.5% and 99% VaR exception diagnostics over 250 days | Counts APL and HPL separately; Phase 7 thresholds preserved | US_R1887_FEDERAL_REGISTER §__.213(b)(3)-(5) | Model-ineligible trigger uses APL or HPL counts at 99.0% and 97.5% over 250 business days | BROADLY_ALIGNED | Independently sourced; re-eligibility and short-history proration are U.S. proposed text | Do not rewrite Phase 7 boundaries | Interpretation note |
| V. Model-eligible / model-ineligible desk routing | BIS_MAR33.40 | Model-ineligible desks use standardized approach context | TD-FX simulated SA fallback; TD-CREDIT selected SA-only | US_R1887_FEDERAL_REGISTER §§__.204(c), __.212-__.213 | Model-eligible desks require approval; model-ineligible positions feed standardized contribution in NDCR | MODIFIED_IN_US_PROPOSAL | U.S. NDCR uses SA_all_desks minus SA_G,A, not simple partial IMA plus selected SA | Phase 8 routing not equivalent | Gap item |
| W. SA fallback mechanics | BIS_MAR33.40 | Model-ineligible desk fallback to SA | Selected SA fallback components only | US_R1887_FEDERAL_REGISTER §__.204(c)-(e) | U.S. has standardized treatment for model-ineligible desks and a separate fallback capital requirement for uncalculable positions | US_SPECIFIC | Two concepts must not be conflated | Add glossary/report distinction | Done in report |
| X. Overall models-based market-risk measure | BIS_MAR33 | Basel final aggregate includes IMCC, SES, DRC, multiplier and surcharge concepts | Final bank-wide aggregate NOT_CALCULATED | US_R1887_FEDERAL_REGISTER §__.204(c) | Models-based measure = NDCR + DRC + fallback capital requirement + redesignation add-ons | MODIFIED_IN_US_PROPOSAL | U.S. final architecture is not Phase 8 aggregation | No U.S. total | Crosswalk only |
| Y. IMA/default-risk treatment | BIS_MAR33 plus MAR22 context | IMA default-risk model out of scope | No IMA default-risk model; selected SA DRC only | US_R1887_FEDERAL_REGISTER §__.210 and §__.204(c) | Default risk capital is a single calculation across model-eligible and model-ineligible positions | MODIFIED_IN_US_PROPOSAL | Project lacks full U.S. DRC and IMA default-risk scope | No code change | Gap matrix |
| Z. Reporting / disclosure | BIS disclosure context out of project scope | Not implemented | No regulatory reports | US_R1887_FEDERAL_REGISTER §__.217 | Proposed quarterly and annual market-risk disclosures and reports | OUT_OF_PROJECT_SCOPE | Reporting controls and attestations absent | Do not claim reporting readiness | Document limitation |

## Instrument-Level RRAO Crosswalk: SYN_EQ_BARRIER

| Instrument | Basel MAR23 project treatment | U.S. proposed treatment | Alignment | Implementation consequence |
| --- | --- | --- | --- | --- |
| SYN_EQ_BARRIER | Other residual risk because the option is path-dependent and has ordinary equity underlying; 0.1% selected RRAO risk weight | Proposed §__.211 includes positions with embedded optionality that have multiple barriers or payoffs not replicable by finite vanilla-option combinations; listed/CCP/back-to-back/fallback exclusions must be assessed independently | BROADLY_ALIGNED | The Phase 4 Basel classification is not automatically a U.S. legal classification. For Phase 9, the barrier is a crosswalk example only and no U.S. RRAO amount is calculated. |

## U.S. Proposed Market-Risk Architecture

```text
Market risk capital framework for covered U.S. banking organizations

Standardized measure for market risk
  = standardized non-default capital requirement
      - sensitivities-based capital requirement
      - residual risk add-on
    + default risk capital requirement
    + fallback capital requirement
    + capital add-ons for redesignations

Models-based measure for market risk
  = NDCR
      - IMA_G,A
      - plus marginal standardized contribution:
        SA_all_desks - SA_G,A
    + default risk capital requirement
    + fallback capital requirement
    + capital add-ons for redesignations
```

Whole-portfolio standardized non-default capital plus partial IMA would double
count model-eligible non-default risk. The U.S. proposed NDCR structure uses
SA_all_desks and subtracts SA_G,A to capture the marginal standardized
contribution from model-ineligible positions.

## Glossary Distinction

Model-ineligible desk standardized treatment: a desk or position cannot use the
models-based non-default capital requirement and is instead included through the
standardized non-default mechanics in the proposed NDCR architecture.

Fallback capital requirement: a separate proposed capital requirement for
positions where the banking organization cannot calculate the relevant
standardized non-default, models-based non-default, or default-risk capital
component. It is not the same term as desk SA fallback.
