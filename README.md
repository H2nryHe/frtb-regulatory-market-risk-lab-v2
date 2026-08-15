# FRTB Regulatory Market Risk Lab V2

This repository is an educational, bounded market-risk lab for selected Basel
Framework market-risk mechanics. It is not a production capital system and does
not make a regulatory compliance claim.

Planned later phases cover non-securitisation DRC, RRAO, selected IMA
ES/liquidity-horizon diagnostics, RFET/modellability, PLA and regulatory VaR
backtesting.

The project is source-traceable: regulatory parameters and scope decisions must
reference frozen official sources before implementation.

Current development status: Phase 3 — SBM Aggregation, Curvature & Correlation
Scenarios.

The current architecture establishes the deterministic chain:

```text
Basel sources -> scope / taxonomy -> sensitivities -> SBM -> DRC -> RRAO -> selected-scope SA capital -> future IMA diagnostics
```

Phase 4 adds selected non-securitisation DRC and selected RRAO, then integrates
them with the binding selected-scope SBM result. The selected-scope Standardised
Approach total is `626510.6801585772`, made up of SBM `601060.6801585773`, DRC
`25200.0`, and RRAO `250.0`. IMA, RFET, PLA and backtesting remain future
diagnostics.
