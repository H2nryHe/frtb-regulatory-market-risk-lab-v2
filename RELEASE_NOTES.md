# Release Notes

## Initial Public Portfolio Release Candidate

### Implemented

- Selected Basel Standardised Approach mechanics for GIRR, Equity and FX.
- Selected non-securitisation DRC and RRAO.
- Selected IMA ES, liquidity-horizon and stress-calibration mechanics.
- Simulated RFET/NMRF classification, PLA and desk VaR backtesting.
- Selected IMCC, NMRF SES and IMA/SA routing case study.
- U.S. 2026 proposed-framework crosswalk.

### Validation Highlights

- Selected-scope SA: about $626.5k.
- RFET: 3 mechanics PASS / 2 mechanics FAIL.
- PLA: 2 GREEN desks / 1 RED desk.
- TD-FX: backtesting PASS but PLA RED, routed to selected SA fallback.
- Final bank-wide aggregate: NOT_CALCULATED.

### Regulatory Scope

The implementation is a selected Basel mechanics lab using deterministic
synthetic data. It is not a filing system and does not establish institutional
model status.

### U.S. 2026 Proposal Crosswalk

R-1887 is treated as PROPOSED / NOT FINAL at the Phase 10 source check. U.S.
proposal parameters remain isolated from Basel calculation configs.

### Known Limitations

No complete seven-risk-class SBM, securitisation DRC, CTP, IMA default-risk
model, bank-wide multiplier, PLA amber surcharge, final MAR33 aggregate,
production market data or U.S. proposal calculation engine is included.

### Reproducibility

The project is intended to run from a clean source tree with editable install,
Ruff, pytest and `python -m frtb_lab.release_validation`.
