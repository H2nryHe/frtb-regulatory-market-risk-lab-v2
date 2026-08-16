# Resume Bullets

## Risk / Model Validation / Quant Risk

- Implemented selected Basel FRTB market-risk mechanics across SBM, non-securitisation DRC, RRAO, 97.5% ES, liquidity horizons, RFET, PLA/backtesting and desk-level IMA/SA routing with source-linked regulatory parameters.
- Built deterministic RFET/NMRF and PLA validation cases across five risk factors and three selected desks, preserving 3 RFET PASS / 2 RFET FAIL outcomes and a TD-FX PLA RED route to selected SA fallback.
- Produced a source-traceable crosswalk to the March 2026 U.S. proposed market-risk framework, documenting material differences in NDCR, Type A / Type B NMRF treatment, fallback capital and applicability without mixing proposal parameters into the Basel engine.

## Quant Dev / Research Tooling

- Designed a reproducible Python package with separated configs, governance artifacts, regulatory registers and calculation modules for selected market-risk capital mechanics.
- Added deterministic regression coverage for selected SA $626.5k, selected IMCC $359.0k, SES $26.7k, RFET/PLA routing outcomes and U.S. proposal parameter isolation.
- Prepared release tooling with editable-install support, GitHub Actions CI, one-command release validation and clean-source-tree reproducibility checks that do not depend on ignored generated artifacts.
