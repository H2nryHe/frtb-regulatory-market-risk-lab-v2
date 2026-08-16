# FRTB Regulatory Market Risk Lab V2

This repository is an educational, bounded market-risk lab for selected Basel
Framework market-risk mechanics. It is not a production capital system and does
not make a regulatory compliance claim.

Completed phases cover selected non-securitisation DRC, selected RRAO,
selected-scope Standardised Approach integration, and provisional selected IMA
ES/liquidity-horizon mechanics, plus simulated RFET mechanics and ES/NMRF
candidate classification. Later phases cover PLA and regulatory VaR
backtesting.

The project is source-traceable: regulatory parameters and scope decisions must
reference frozen official sources before implementation.

Current development status: Phase 6 — RFET, Simulated Modellability Assessment
& NMRF Classification.

The current architecture establishes the deterministic chain:

```text
Basel sources -> scope / taxonomy -> sensitivities -> SBM -> DRC -> RRAO -> selected-scope SA capital -> synthetic history -> 10-day ES -> liquidity horizons -> stressed calibration -> simulated RFET mechanics -> ES / NMRF candidate classification -> future PLA / backtesting
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

Phase 6 adds simulated RFET mechanics under BIS MAR31 using deterministic
synthetic observation events. Passing factors are labelled only
`ES_CANDIDATE_PENDING_REAL_DATA_VALIDATION`; failing factors are labelled
`NMRF_CANDIDATE` with NMRF stress-scenario capital deferred. This is not
regulatory modellability certification.
