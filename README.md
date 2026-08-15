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
official sources -> trading-book scope -> regulatory sensitivities -> risk weights -> bucket aggregation -> correlation scenarios -> selected-scope SBM capital
```

Phase 3 adds selected-scope SBM aggregation for GIRR, Equity and FX delta,
Equity and FX vega, and selected vanilla Equity/FX curvature. The generated
LOW, MEDIUM and HIGH scenario totals are all `601060.6801585773`; the reported
selected-scope SBM capital is the maximum of those scenario totals. DRC, RRAO
calculation and IMA remain unimplemented.
