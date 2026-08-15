# FRTB Regulatory Market Risk Lab V2

This repository is an educational, bounded market-risk lab for selected Basel
Framework market-risk mechanics. It is not a production capital system and does
not make a regulatory compliance claim.

Planned later phases cover selected GIRR, Equity and FX SBM mechanics,
non-securitisation DRC, RRAO, selected IMA ES/liquidity-horizon diagnostics,
RFET/modellability, PLA and regulatory VaR backtesting.

The project is source-traceable: regulatory parameters and scope decisions must
reference frozen official sources before implementation.

Current development status: Phase 2 — Regulatory Sensitivities, Bucketing &
Parameter Freeze.

The current architecture establishes the deterministic chain:

```text
source -> scope -> instrument -> risk factor -> regulatory sensitivity -> bucket / risk weight -> future aggregation -> future capital
```

Phase 2 adds deterministic synthetic market inputs, selected GIRR/Equity/FX
delta sensitivities, selected Equity/FX vega sensitivities, selected bucket
mapping, and source-linked risk weights. It does not calculate within-bucket
capital, cross-bucket capital, correlation scenarios, DRC, RRAO or IMA results.
