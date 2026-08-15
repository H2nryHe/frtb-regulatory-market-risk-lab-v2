# SBM Aggregation, Curvature and Correlation Scenarios

## Purpose

Phase 3 implements a selected educational Basel SBM aggregation path for the
numerical scope already established in Phase 2. It is not a production or
regulatory-compliance capital engine.

The implemented chain is:

```text
raw sensitivities -> net regulatory risk factors -> weighted sensitivities -> bucket capital -> risk-class capital -> LOW/MEDIUM/HIGH totals -> selected-scope SBM capital
```

## Regulatory Basis

The source is BIS_MAR21 from the frozen source register, using MAR21.1-MAR21.7
for the SBM structure, MAR21.4 for delta/vega aggregation, MAR21.5 for
curvature, MAR21.6 for correlation scenarios, MAR21.7 for scenario selection,
and the selected GIRR, Equity, FX, vega and curvature sections in
MAR21.41-MAR21.101.

## Phase 2 Coverage Audit

`SYN_EQ_INDEX` and `SYN_EQ_CALL` are treated as Equity bucket 12 only under the
documented synthetic assumption that `SYN_SPX_INDEX` is a recognised broad
index with at least 75% large-cap advanced-economy constituents. This is an
educational mapping assumption for a synthetic index, not a regulatory
determination for a real index.

The canonical market state contains an equity repo-rate field, but the project
pricing functions for `SYN_EQ_INDEX` and `SYN_EQ_CALL` do not consume it.
Phase 3 tests change the repo rate and prove the selected equity spot delta is
unchanged, so no equity repo sensitivity is produced. The coverage table records
those rows as `NOT_APPLICABLE`, not silently omitted.

`governance/sbm_sensitivity_coverage.csv` lists every canonical instrument and
pricing risk input reviewed. Material deferred items include equity option
rate/dividend sensitivities, FX forward and option rate sensitivities, corporate
bond CSR/DRC inputs, and barrier spot/volatility sensitivity.

## Numerical Scope

Numerically included selected SBM rows are:

| Risk class | Sensitivity type | Instruments |
| --- | --- | --- |
| GIRR | delta | `SYN_USD_GOVT_5Y`, `SYN_USD_IRS_5Y` |
| Equity | delta | `SYN_EQ_INDEX`, `SYN_EQ_CALL` |
| FX | delta | `SYN_EURUSD_FWD`, `SYN_EURUSD_CALL` |
| Equity | vega | `SYN_EQ_CALL` |
| FX | vega | `SYN_EURUSD_CALL` |
| Equity | curvature | `SYN_EQ_CALL` |
| FX | curvature | `SYN_EURUSD_CALL` |

## Netting Before Risk Weighting

Phase 3 first nets raw sensitivities by regulatory risk factor, then applies
the risk weight. The canonical selected scope has 8 raw Phase 2 sensitivity
rows and 5 net delta/vega regulatory risk factors:

| Risk class | Sensitivity | Bucket | Net weighted sensitivity |
| --- | --- | --- | ---: |
| GIRR | delta | USD | -153309.2302785498 |
| Equity | delta | EQUITY_BUCKET_12 | 153024.3684328582 |
| FX | delta | EUR/USD | 225542.7953442151 |
| Equity | vega | EQUITY_BUCKET_12 | 30510.6529200413 |
| FX | vega | EUR/USD | 38673.6331829128 |

Meaningful canonical netting occurs for GIRR, where the government bond and IRS
share `RF_GIRR_USD_5Y`, and for Equity and FX spot delta, where the cash/forward
and option rows share the same selected risk factor.

## Delta Aggregation

| Scenario | GIRR | Equity | FX |
| --- | ---: | ---: | ---: |
| LOW | 153309.2302785498 | 153024.3684328582 | 225542.7953442151 |
| MEDIUM | 153309.2302785498 | 153024.3684328582 | 225542.7953442151 |
| HIGH | 153309.2302785498 | 153024.3684328582 | 225542.7953442151 |

The canonical selected scope has one bucket per implemented delta risk-class
slice, so the LOW/MEDIUM/HIGH transforms do not change these capital amounts.
Non-trivial correlation behavior is covered by deterministic test fixtures.

## Vega Aggregation

| Scenario | Equity | FX |
| --- | ---: | ---: |
| LOW | 30510.6529200413 | 38673.6331829128 |
| MEDIUM | 30510.6529200413 | 38673.6331829128 |
| HIGH | 30510.6529200413 | 38673.6331829128 |

The code supports the selected delta-risk-factor correlation component and the
option maturity correlation `exp(-alpha * abs(Tk - Tl) / min(Tk, Tl))` with
`alpha=0.01`. A two-maturity test fixture exercises this formula because the
canonical portfolio has only 1Y options.

## Curvature Method

Selected Equity and FX curvature uses full revaluation for the vanilla option
positions. CVR values are represented as loss-positive:

```text
CVR_up = -(value_up - value_base - delta * shock)
CVR_down = -(value_down - value_base + delta * shock)
```

| Instrument | Shock | CVR up | CVR down | Scenario direction | Capital |
| --- | ---: | ---: | ---: | --- | ---: |
| `SYN_EQ_CALL` | 0.15 | -9159.6147814098 | -12043.2095174542 | no positive curvature loss | 0.0000000000 |
| `SYN_EURUSD_CALL` | 0.15 | -23950.9335951758 | -29760.8896193567 | no positive curvature loss | 0.0000000000 |

Both selected long vanilla calls have negative loss-positive CVR values after
delta removal under the configured synthetic market state. Curvature capital is
therefore zero, while full revaluation and delta removal are still performed and
tested.

## Low / Medium / High Correlation Scenarios

MEDIUM uses selected frozen rho and gamma values. HIGH applies
`min(1.25 * correlation, 1.0)`. LOW applies
`max(2 * correlation - 1, 0.75 * correlation)`. Only correlations change
between scenarios; raw sensitivities, net sensitivities, risk weights, market
state and portfolio terms are unchanged.

## Negative-Radicand / Alternative Aggregation Rule

Across-bucket aggregation explicitly detects a negative radicand and recalculates
with the alternative `S_b` convention `max(min(S_b, K_b), -K_b)`. The canonical
selected portfolio does not trigger this branch, so a deterministic test fixture
forces it and verifies the alternative result.

## Selected-Scope Capital Results

| Scenario | GIRR delta | Equity delta | FX delta | Equity vega | FX vega | Equity curvature | FX curvature | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| LOW | 153309.2302785498 | 153024.3684328582 | 225542.7953442151 | 30510.6529200413 | 38673.6331829128 | 0.0000000000 | 0.0000000000 | 601060.6801585773 |
| MEDIUM | 153309.2302785498 | 153024.3684328582 | 225542.7953442151 | 30510.6529200413 | 38673.6331829128 | 0.0000000000 | 0.0000000000 | 601060.6801585773 |
| HIGH | 153309.2302785498 | 153024.3684328582 | 225542.7953442151 | 30510.6529200413 | 38673.6331829128 | 0.0000000000 | 0.0000000000 | 601060.6801585773 |

Binding scenario: LOW, MEDIUM and HIGH tie. The selected-scope SBM capital is
`601060.6801585773`.

## Capital Attribution

FX delta is the largest selected component at `225542.7953442151`, followed by
GIRR delta at `153309.2302785498` and Equity delta at `153024.3684328582`.
Selected vega capital contributes `69184.2861029541` across Equity and FX.
Selected curvature contributes zero under the synthetic long-option setup after
delta removal.

## Independent Checks

Tests cover one-factor bucket capital, perfect same-risk-factor offsetting,
same-bucket two-factor aggregation, cross-bucket aggregation, negative-radicand
alternative aggregation, LOW/MEDIUM/HIGH correlation transforms, high cap, low
formula branch behavior, two-maturity vega correlation, curvature full
revaluation, curvature sign discipline, squared-delta curvature correlations,
scenario-specific curvature direction selection, and final scenario max
selection.

For selected vanilla options, the full regulatory shock is intentionally not
expected to equal a small-shock gamma approximation. Convexity diagnostics are
useful for sign sanity, but the capital calculation uses full revaluation.

## Excluded Sensitivities / Instruments

Excluded numerical sensitivities are explicit in
`governance/sbm_sensitivity_coverage.csv`. They include:

- equity option USD rate and dividend/carry sensitivity;
- FX forward and FX option domestic and foreign rate sensitivity;
- corporate bond CSR sensitivity and default jump risk;
- barrier option spot and volatility sensitivity.

The barrier option remains an Equity instrument and RRAO candidate, but no fake
barrier curvature or RRAO charge is calculated.

## Limitations

The Phase 3 number must be read only as selected-scope SBM capital for a
synthetic educational portfolio. It is not FRTB capital, portfolio regulatory
capital, a legal classification of a real index, or a complete Standardised
Approach implementation.

## Explicitly Deferred Components

DRC capital, RRAO calculation, IMA expected shortfall, RFET, modellability,
PLA, backtesting, production governance and supervisory reporting remain
deferred.
