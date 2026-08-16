# FRTB Regulatory Market Risk Capital & Validation Lab

Source-traceable educational implementation of selected Basel FRTB market-risk
mechanics spanning the Standardised Approach, IMA Expected Shortfall, liquidity
horizons, RFET/NMRF classification, PLA/backtesting and desk-level IMA/SA
routing, with a separate crosswalk to the March 2026 U.S. proposed market-risk
framework.

The project uses deterministic synthetic positions and histories. It is not a
complete Basel implementation, not an operational bank system, and not a current
U.S. rule implementation.

Phase 9 adds a Regulatory Crosswalk for the U.S. 2026 proposed market-risk framework.
It is a selected-scope crosswalk and validation package for the proposal; it does not claim U.S. regulatory compliance and does not treat R-1887 as final.
It does not produce a U.S. proposal capital number.

## What This Project Demonstrates

- Selected Basel market-risk capital mechanics with source-linked parameters.
- Model-validation workflow: RFET, PLA, backtesting, findings and routing.
- Adverse outcomes preserved instead of tuned away.
- Clear separation between Basel calculations and U.S. proposal crosswalks.
- Offline deterministic tests and release validation.

## Architecture

```text
OFFICIAL SOURCES
        |
        v
TRADING BOOK / RISK FACTORS
        |
        +--------------------------+
        |                          |
        v                          v
STANDARDISED APPROACH          IMA DIAGNOSTICS
SBM                            10-day ES
DRC                            Liquidity horizons
RRAO                           Stress calibration
        |                      RFET
        |                      PLA / Backtesting
        |                          |
        |                    Desk Routing
        |                    /          \
        |                IMA branch     SA fallback
        |                /      \
        |             IMCC      NMRF SES
        |
        +--------> SELECTED ROUTING CASE STUDY

U.S. 2026 proposed framework -> regulatory crosswalk only
```

## Selected Results

| Area | Result |
| --- | --- |
| Selected SBM | about $601.1k |
| Selected-scope SA | about $626.5k |
| RFET factors | 3 mechanics PASS / 2 mechanics FAIL |
| PLA desks | 2 GREEN / 1 RED |
| TD-FX | backtesting PASS but PLA RED -> simulated SA fallback |
| Selected IMCC mechanics | about $359.0k |
| Selected SES mechanics | about $26.7k |
| Final bank-wide aggregate | NOT_CALCULATED |
| U.S. proposal | PROPOSED / CROSSWALK ONLY |

The SA and IMA component figures are intentionally not a like-for-like comparison; the project does not calculate the complete
final bank-wide IMA vs SA total.

## Standardised Approach

Implemented selected GIRR, Equity and FX SBM mechanics: delta, vega, curvature,
within-bucket aggregation, cross-bucket aggregation and LOW/MEDIUM/HIGH
correlation scenarios. Phase 4 adds selected non-securitisation DRC and RRAO.

## IMA Mechanics

Implemented selected 97.5% ES mechanics using direct overlapping 10-business-day
synthetic shocks, the 10/20/40/60/120-day liquidity-horizon grid, reduced-set
stress calibration and selected IMCC mechanics.

## RFET / NMRF

Five selected risk factors are evaluated with simulated RFET mechanics. Three
pass and two fail. Equity volatility and FX spot become NMRF candidates. The
original reduced set fails RFET validation and is preserved as an open finding.

Synthetic observations are not institutional real-price evidence.

## PLA / Backtesting

TD-RATES and TD-EQUITY are PLA GREEN and pass selected VaR backtesting. TD-FX
passes selected backtesting but fails PLA because the RTPL design omits
volatility and has a spot-sign mismatch.

## Capital Routing Case Study

TD-RATES and TD-EQUITY route to the simulated IMA branch. TD-FX routes to
selected SA fallback due PLA RED. TD-CREDIT remains selected SA-only and outside
the selected IMA diagnostic scope.

NMRF status alone does not force desk fallback: TD-EQUITY remains on the IMA
branch while its equity-volatility NMRF candidate enters selected SES mechanics.

## U.S. 2026 Proposal Crosswalk

Phase 9 compares selected Basel mechanics with official March 2026 U.S. proposed
rulemaking sources for R-1887. It documents material U.S.-specific differences,
including applicability thresholds, models-based NDCR architecture, Type A /
Type B NMRF treatment, fallback capital and reporting scope.

U.S. proposal parameters remain isolated from Basel calculation configs. No U.S.
proposal capital number is produced.

## Validation & Reproducibility

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m frtb_lab.release_validation
```

Release validation prints a concise regression summary and does not require
ignored generated artifacts.

## Repository Structure

| Path | Purpose |
| --- | --- |
| `configs/` | selected regulatory and synthetic-model configuration |
| `regulatory/` | source registers, parameter crosswalks and U.S. proposal analysis |
| `governance/` | desk/factor inventories, findings and routing evidence |
| `src/frtb_lab/` | Python package for calculations and release validation |
| `tests/` | deterministic unit, regression, source and claim tests |
| `reports/` | final validation, recruiter summary and methodology sections |

Generated artifacts under `data/artifacts/` are reproducible locally and are
ignored by default.

## Suggested Review Path

2 minutes: README + Selected Results.

5 minutes: README + `reports/RECRUITER_AND_INTERVIEW_SUMMARY.md`.

Technical review: `reports/FRTB_V2_FINAL_VALIDATION_REPORT.md`, tests and
`regulatory/us_2026_proposal_crosswalk.md`.

## Regulatory Sources

Basel mechanics are sourced from official BIS MAR20, MAR21, MAR22, MAR23,
MAR30, MAR31, MAR32 and MAR33 chapters. U.S. proposal analysis uses official
Federal Reserve, Federal Register, OCC and FDIC sources recorded in
`regulatory/source_register.yaml`.

## Scope & Limitations

Out of scope: complete seven-risk-class SBM, full CSR, commodity,
securitisation DRC, CTP, IMA default-risk model, bank-wide multiplier, PLA amber
surcharge, final MAR33 aggregate, production market data, regulatory reporting
and a U.S. proposal calculation engine.

Final bank-wide aggregate remains `NOT_CALCULATED`.
