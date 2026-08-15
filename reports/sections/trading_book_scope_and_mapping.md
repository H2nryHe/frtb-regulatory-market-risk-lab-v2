# Trading Book Scope and Risk-Factor Mapping

## Purpose

Phase 1 creates the controlled data model that later selected Basel
market-risk mechanics will operate on. It defines a deterministic synthetic
educational portfolio and validates the chain from instrument to trading desk,
trading-book scope, primary risk class, mapped risk factors and future treatment
flags.

## Regulatory Basis

The mapping uses the frozen Phase 0 source register. BIS_MAR20 provides the
standardised-approach structure used for scope boundaries. BIS_MAR21 provides
selected GIRR, Equity and FX risk-factor and sensitivity taxonomy. BIS_MAR22 is
used only to flag future non-securitisation DRC relevance. BIS_MAR23 is used
only to flag future RRAO relevance for path-dependent/exotic examples.

No U.S. proposal implementation logic is changed in Phase 1.

## Synthetic Portfolio

The canonical fixture is `data/fixtures/canonical_portfolio.yaml`. It contains
four synthetic desks and eight synthetic instruments:

- `TD-RATES`: `SYN_USD_GOVT_5Y`, `SYN_USD_IRS_5Y`
- `TD-EQUITY`: `SYN_EQ_INDEX`, `SYN_EQ_CALL`, `SYN_EQ_BARRIER`
- `TD-FX`: `SYN_EURUSD_FWD`, `SYN_EURUSD_CALL`
- `TD-CREDIT`: `SYN_CORP_BOND`

These are not actual bank positions, not a regulatory portfolio submission and
not live market data.

## Trading Desk Structure

The tracked desk inventory is `governance/trading_desk_inventory.csv`. Every
instrument in the canonical fixture references one known synthetic desk, and
each desk is labelled as a synthetic educational example.

## Instrument Taxonomy

The tracked instrument inventory is `governance/instrument_inventory.csv`.
Phase 1 instrument records include identifiers, desk ownership, currency,
notional metadata, maturity/tenor, optionality, exotic, securitisation,
trading-book and future-treatment flags.

The Python instrument classes in `src/frtb_lab/instruments/` are intentionally
lightweight metadata records. They do not price instruments.

## Risk-Factor Taxonomy

The tracked risk-factor inventory is `governance/risk_factor_inventory.csv`.
It covers only selected future needs:

- GIRR: USD five-year risk-free yield-curve tenor taxonomy.
- Equity: selected SPX-like spot and one-year implied-volatility taxonomy.
- FX: selected EUR/USD spot and one-year implied-volatility taxonomy.
- Credit: one synthetic corporate issuer default reference for future
  non-securitisation DRC preparation.

The project does not create the full Basel risk-factor universe in Phase 1.

## Sensitivity Requirement Mapping

The tracked mapping register is `regulatory/sensitivity_mapping.csv`. It records
future treatment requirements only. Vanilla options are marked for later delta,
vega and curvature treatment; linear instruments are marked for later delta
treatment where selected; the corporate bond is marked as DRC-relevant; and the
barrier option is marked as an RRAO candidate.

No sensitivity values, risk weights, correlation parameters or aggregation
formulas are implemented.

## DRC / RRAO Preparation

`SYN_CORP_BOND` is explicitly marked as a future non-securitisation DRC
candidate. `SYN_EQ_BARRIER` is explicitly marked as exotic/path-dependent and
as an RRAO candidate. These flags support future phases only.

## Validation Controls

`src/frtb_lab/mapping/scope.py` validates that:

- every instrument belongs to a known desk,
- trading-book scope is explicit,
- selected instruments map to supported primary risk classes,
- securitisations are rejected from the selected fixture,
- unsupported instrument/risk-class combinations fail loudly,
- option and exotic flags are consistent,
- DRC and RRAO preparation flags are explicit,
- every risk factor references known instruments.

Negative tests cover duplicate instrument IDs, unknown desks, unsupported
mappings, securitisation entry, inconsistent option metadata, inconsistent
exotic metadata, and DRC flag inconsistency.

## Explicitly Deferred Calculations

Phase 1 does not implement SBM capital, DRC capital, RRAO capital, IMA ES, RFET,
PLA or regulatory backtesting. It also does not add risk-weight tables,
correlation parameters, DRC weights or PLA thresholds.

## Limitations

The portfolio is deliberately small and synthetic. It is suitable for
deterministic educational tests and later hand-checkable examples, but it should
not be interpreted as a complete bank trading-book representation or a
regulatory filing artifact.
