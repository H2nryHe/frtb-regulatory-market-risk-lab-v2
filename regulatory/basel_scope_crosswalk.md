# Basel Scope Crosswalk

Scope document for the current phase gate. It records completed source
governance and Phase 1 taxonomy/mapping work before any capital formula or
eligibility calculation is implemented.

| Basel chapter / paragraph area | Concept | Planned project phase | Implementation scope | Explicitly omitted scope | Source ID |
| --- | --- | --- | --- | --- | --- |
| MAR20.1-MAR20.5 | Standardised approach structure | Phase 0 source governance; later SA phases | Use as organizing source for selected SA components only | Full SA coverage and market-risk RWA reporting | BIS_MAR20 |
| MAR21.1-MAR21.101 | Sensitivities-based method | Phases 2-3 | Planned selected GIRR SBM, Equity SBM and FX SBM, including delta, vega, curvature, bucket aggregation and correlation scenarios | Full seven-risk-class SBM; CSR non-securitisation, securitisation, CTP and commodity implementation | BIS_MAR21 |
| MAR22.1-MAR22.26 | Default risk capital requirement | Phase 4 | Planned non-securitisation DRC for controlled corporate, sovereign and local-government/municipality examples | Securitisation DRC, non-CTP securitisation and CTP | BIS_MAR22 |
| MAR23.1-MAR23.8 | Residual Risk Add-On | Phase 4 | Planned bounded RRAO classifier and calculator for deterministic examples | Exhaustive product taxonomy and reporting workflow | BIS_MAR23 |
| MAR30.1-MAR30.18 | Internal models approach governance | Phases 5-7 | Planned documentation and diagnostics for selected IMA workflow concepts | Supervisory model application workflow and bank approval processes | BIS_MAR30 |
| MAR31.1-MAR31.26 | Model requirements and RFET | Phase 6 | Planned RFET and modellability classification for synthetic real-price observations | Full NMRF stressed expected-shortfall capital engine | BIS_MAR31 |
| MAR32.1-MAR32.45 | Backtesting and PLA | Phase 7 | Planned PLA diagnostics and regulatory VaR backtesting for synthetic desks | Production desk governance and regulatory filing | BIS_MAR32 |
| MAR33.1-MAR33.17 | ES and liquidity horizons | Phase 5 | Planned selected IMA ES and liquidity-horizon mechanics | Full bank-wide IMCC implementation and complete SES engine | BIS_MAR33 |
| MAR33.40-MAR33.46 | Model-ineligible desks and aggregation context | Phase 7 documentation; Phase 8 case study | Planned fallback-to-SA diagnostic interpretation for controlled desks | Single bank-wide total capital claim | BIS_MAR33 |
| MAR20.1-MAR20.5 and MAR21 selected taxonomy paragraphs | Trading-book scope representation | Phase 1 | Implemented deterministic synthetic instrument-to-desk scope metadata and validation controls | Legal entity scope, supervisory reporting and production trading-book governance | BIS_MAR20; BIS_MAR21 |
| MAR21.8, MAR21.12, MAR21.14, MAR21.19, MAR21.21, MAR21.24-MAR21.28 | Instrument taxonomy and risk-factor mapping | Phase 1 | Implemented selected GIRR, Equity and FX taxonomy records needed for later phases | Full Basel risk-factor universe and risk-weight tables | BIS_MAR21 |
| MAR21.1-MAR21.7 and MAR21.15-MAR21.38 | Sensitivity requirement mapping | Phase 1 | Implemented metadata describing future delta, vega and curvature treatment requirements | Sensitivity values, risk weights and SBM aggregation | BIS_MAR21 |
| MAR22.1 and MAR22.9-MAR22.26 | Credit / DRC preparation | Phase 1 | Implemented explicit non-securitisation corporate credit flagging for later DRC work | DRC JTD, netting, HBR, risk weights and capital calculation | BIS_MAR22 |
| MAR23.2-MAR23.5 | Exotic / RRAO preparation | Phase 1 | Implemented explicit path-dependent barrier-option flagging for later RRAO work | RRAO gross-notional charge and residual-risk capital calculation | BIS_MAR23 |

Explicit out-of-scope items for this project version: securitisation DRC, CTP,
full seven-risk-class SBM, full NMRF SES capital engine, full bank-wide IMCC
implementation, and regulatory reporting or filing.
