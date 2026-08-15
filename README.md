# FRTB Regulatory Market Risk Lab V2

This repository is an educational, bounded market-risk lab for selected Basel
Framework market-risk mechanics. It is not a production capital system and does
not make a regulatory compliance claim.

Planned later phases cover selected GIRR, Equity and FX SBM mechanics,
non-securitisation DRC, RRAO, selected IMA ES/liquidity-horizon diagnostics,
RFET/modellability, PLA and regulatory VaR backtesting.

The project is source-traceable: regulatory parameters and scope decisions must
reference frozen official sources before implementation.

Current development status: Phase 1 — Trading Book Scope, Instrument Taxonomy
& Risk-Factor Inventory.

The current architecture establishes the deterministic chain:

```text
synthetic portfolio -> trading desk -> risk class -> risk factor -> future sensitivity treatment
```

Phase 1 adds the canonical synthetic portfolio, desk inventory, instrument
inventory, risk-factor inventory, sensitivity requirement mapping, and
validation controls. It does not calculate FRTB capital.
