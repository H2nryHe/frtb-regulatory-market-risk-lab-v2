# Public Release File Inventory

## Include in public repository

## Code

- `src/frtb_lab/`: package code for selected instruments, pricing helpers,
  sensitivities, mapping, Standardised Approach and selected IMA diagnostics.
- `src/frtb_lab/release_validation.py`: one-command release regression wrapper.

## Configuration

- `configs/sa/`: selected source-linked SA parameters.
- `configs/ima/`: selected IMA, RFET, reduced-set and desk model configs.
- `data/fixtures/`: deterministic synthetic portfolio and market-state inputs.

## Regulatory Source / Crosswalk

- `regulatory/source_register.yaml`: official source register.
- `regulatory/parameter_crosswalk.csv`: Basel/project parameter provenance.
- `regulatory/us_2026_*`: U.S. 2026 proposed-framework status, crosswalk,
  parameters and gap analysis.
- `regulatory/us_source_interpretation_notes.md`: documented U.S. proposal text
  ambiguity.

## Governance

- `governance/*`: desk, factor, coverage, findings, routing, scope and final
  findings inventories.

## Tests

- `tests/`: deterministic unit, regression, source, claim and release tests.

## Reports

- `reports/sections/`: phase-level methodology reports.
- `reports/FRTB_V2_FINAL_VALIDATION_REPORT.md`: final integrated validation
  report.
- `reports/RECRUITER_AND_INTERVIEW_SUMMARY.md`: concise interview guide.
- `reports/RESUME_BULLETS.md`: resume-ready bullet options.
- `reports/final_validation_snapshot.md`: release snapshot.

## CI

- `.github/workflows/ci.yml`: GitHub Actions quality, tests and release
  validation workflow.

## Keep local / ignored

- `PROJECT_FRTB_V2_SPEC.md`
- `FRTB_V2_STATUS.md`
- `local_frtb_v2_baseline/`
- `data/artifacts/*` other than `.gitkeep`
- caches, virtual environments, local IDE files and generated temporary output
