# FRTB Regulatory Market Risk Lab V2

This repository is an educational, bounded market-risk lab for selected Basel
Framework market-risk mechanics. It is not a production risk engine and does not
make a regulatory compliance claim.

Completed phases cover selected non-securitisation DRC, selected RRAO,
selected-scope Standardised Approach integration, and provisional selected IMA
ES/liquidity-horizon mechanics, plus simulated RFET mechanics and ES/NMRF
candidate classification, plus desk-level PLA, regulatory VaR backtesting and
simulated IMA diagnostic status, plus selected IMCC, NMRF stress-scenario and
integrated IMA/SA routing mechanics.

The project is source-traceable: regulatory parameters and scope decisions must
reference frozen official sources before implementation.

Current development status: Phase 9 — U.S. 2026 Proposed Market Risk Framework
Crosswalk.

The current architecture establishes the deterministic chain:

```text
Basel sources -> scope / taxonomy -> sensitivities -> SBM -> DRC -> RRAO -> selected-scope SA capital -> synthetic history -> 10-day ES -> liquidity horizons -> stressed calibration -> simulated RFET mechanics -> ES / NMRF candidate classification -> HPL / RTPL / synthetic APL -> PLA / desk VaR backtesting -> simulated desk diagnostic -> selected IMCC / SES mechanics -> component routing matrix -> U.S. 2026 proposal crosswalk
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

Phase 7 adds deterministic MAR32 desk-level PLA and VaR backtesting diagnostics.
Canonical selected desks use 250-day HPL, RTPL and synthetic APL samples. TD-RATES
and TD-EQUITY are GREEN/PASS simulated desk diagnostics; TD-FX is a simulated
SA fallback diagnostic due PLA RED. Phase 7 does not calculate final IMCC, NMRF
stress-scenario capital, a PLA amber surcharge, bank-wide approval or Phase 8
aggregation.

Phase 8 adds selected MAR33 IMCC mechanics for TD-RATES and TD-EQUITY, selected
NMRF stress-scenario mechanics for the TD-EQUITY equity-volatility candidate,
and an integrated routing matrix. The selected IMCC component is
`358979.94225370314`; the selected SES component is `26655.82413840059`.
TD-FX is routed to selected SA fallback components and TD-CREDIT remains selected
SA-only for the controlled case study. The final bank-wide aggregate is not
calculated.

## Regulatory Crosswalk

```text
Basel implementation
        <->
U.S. 2026 proposed market-risk framework
```

Phase 9 compares selected Basel mechanics with official March 2026 U.S.
proposed rulemaking sources for R-1887. It documents material U.S.-specific
differences, including applicability thresholds, standardized non-default
capital, models-based NDCR architecture, Type A / Type B NMRF treatment,
fallback capital, PLA/backtesting and reporting scope.

The U.S. proposal material is source-traceable and crosswalk-only. The project
does not claim U.S. regulatory compliance, does not treat R-1887 as final, and
does not produce a U.S. proposal capital number.
