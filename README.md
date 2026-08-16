# FRTB Regulatory Market Risk Lab V2

This repository is an educational, bounded market-risk lab for selected Basel
Framework market-risk mechanics. It is not a production capital system and does
not make a regulatory compliance claim.

Completed phases cover selected non-securitisation DRC, selected RRAO,
selected-scope Standardised Approach integration, and provisional selected IMA
ES/liquidity-horizon mechanics. Later phases cover RFET/modellability, PLA and
regulatory VaR backtesting.

The project is source-traceable: regulatory parameters and scope decisions must
reference frozen official sources before implementation.

Current development status: Phase 5 — IMA Expected Shortfall Mechanics,
Liquidity Horizons & Stress Calibration.

The current architecture establishes the deterministic chain:

```text
Basel sources -> scope / taxonomy -> sensitivities -> SBM -> DRC -> RRAO -> selected-scope SA capital -> provisional selected IMA ES mechanics -> future RFET / PLA / backtesting
```

Phase 4 adds selected non-securitisation DRC and selected RRAO, then integrates
them with the binding selected-scope SBM result. The selected-scope Standardised
Approach total is `626510.6801585772`, made up of SBM `601060.6801585773`, DRC
`25200.0`, and RRAO `250.0`.

Phase 5 adds **PROVISIONAL IMA ES MECHANICS** for selected synthetic risk
factors under BIS MAR33. Current full-set liquidity-adjusted ES is
`135310.97891484312`; provisional reduced-set current ES is
`136600.78255244752`; scaled stressed ES is `377307.3028054556`. RFET,
modellability, NMRF capital, PLA, backtesting, desk eligibility, final IMCC
aggregation and IMA default risk model remain deferred.
