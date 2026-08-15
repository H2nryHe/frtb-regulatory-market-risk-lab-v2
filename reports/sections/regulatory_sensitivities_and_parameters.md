# Regulatory Sensitivities and Parameter Freeze

## Purpose

Phase 2 implements selected raw and weighted regulatory sensitivities for GIRR,
Equity and FX. It freezes only the Basel MAR21 parameters needed for this
selected scope and stops before within-bucket aggregation, cross-bucket
aggregation, correlation scenarios or SBM capital.

## Official Regulatory Basis

The official source is BIS_MAR21 from the frozen source register. The selected
source areas are MAR21.8, MAR21.12, MAR21.14, MAR21.15-MAR21.30,
MAR21.39-MAR21.50, MAR21.72-MAR21.80, MAR21.86-MAR21.95 and
MAR21.96-MAR21.101 for curvature provenance only.

## Selected Scope

Numerical sensitivities are produced for:

- `SYN_USD_GOVT_5Y`
- `SYN_USD_IRS_5Y`
- `SYN_EQ_INDEX`
- `SYN_EQ_CALL`
- `SYN_EURUSD_FWD`
- `SYN_EURUSD_CALL`

`SYN_CORP_BOND` is classified as CSR non-securitisation and remains separately
marked `drc_relevant=true`; no DRC is calculated. `SYN_EQ_BARRIER` remains an
Equity instrument with `rrao_candidate=true`; no barrier sensitivity is invented
and no RRAO is calculated.

## Canonical Synthetic Market State

The canonical market state is `data/fixtures/canonical_market_state.yaml`.
Reporting currency is USD. EUR/USD is quoted as USD per EUR. Rates are annual
continuously compounded decimal zero rates. Volatilities are annual implied
volatilities in decimal units. All inputs are synthetic and deterministic.

## Valuation Assumptions

The pricing layer is deliberately small:

- fixed-rate bond: deterministic discounted cash flows;
- vanilla IRS: receive-fixed value using a synthetic par-rate relation;
- equity index: units times spot;
- equity option: Black-Scholes-style call with dividend yield;
- FX forward: discounted long-foreign forward value;
- FX option: Garman-Kohlhagen-style call.

These are project valuation functions only, used to support regulatory
sensitivity calculations. They are not a full pricing library.

## GIRR Delta / PV01

GIRR PV01 applies a 1bp absolute bump and divides the value change by `0.0001`.
The raw sensitivity unit is USD per 1.0 absolute rate move after the Basel bump
division.

| Instrument | Bucket | Tenor | Raw sensitivity | Risk weight | Weighted sensitivity |
| --- | --- | --- | ---: | ---: | ---: |
| `SYN_USD_GOVT_5Y` | USD | 5Y | -4681071.5352499392 | 0.011000 | -51491.7868877493 |
| `SYN_USD_IRS_5Y` | USD | 5Y | -9256131.2173455004 | 0.011000 | -101817.4433908005 |

## Equity Delta

Equity spot delta applies a 1% relative spot shock and divides the value change
by `0.01`. The synthetic index is mapped to bucket 12 under the documented
large-market-cap advanced-economy index assumption. Equity repo-rate
sensitivity is explicitly outside selected Phase 2 scope.

| Instrument | Bucket | Tenor | Raw sensitivity | Risk weight | Weighted sensitivity |
| --- | --- | --- | ---: | ---: | ---: |
| `SYN_EQ_INDEX` | EQUITY_BUCKET_12 | spot | 750000.0000000000 | 0.150000 | 112500.0000000000 |
| `SYN_EQ_CALL` | EQUITY_BUCKET_12 | spot | 270162.4562190547 | 0.150000 | 40524.3684328582 |

## FX Delta

FX delta applies a 1% relative EUR/USD shock and divides the USD value change
by `0.01`. The quote convention is USD per EUR and the project reporting
currency is USD. The base 15% FX risk weight is used; the discretionary
specified-currency-pair reduction is not used.

| Instrument | Bucket | Tenor | Raw sensitivity | Risk weight | Weighted sensitivity |
| --- | --- | --- | ---: | ---: | ---: |
| `SYN_EURUSD_FWD` | EUR/USD | spot | 1088510.4258246957 | 0.150000 | 163276.5638737043 |
| `SYN_EURUSD_CALL` | EUR/USD | spot | 415108.2098034050 | 0.150000 | 62266.2314705108 |

## Vega

Pricing-model vega is not treated as the regulatory vega sensitivity. The
regulatory vega sensitivity is model vega multiplied by implied volatility.
Option maturity tenors are frozen as 0.5, 1, 3, 5 and 10 years.

| Instrument | Bucket | Tenor | Raw regulatory vega | Risk weight | Weighted sensitivity |
| --- | --- | --- | ---: | ---: | ---: |
| `SYN_EQ_CALL` | EQUITY_BUCKET_12 | 1Y | 39226.8615582943 | 0.777800 | 30510.6529200413 |
| `SYN_EURUSD_CALL` | EUR/USD | 1Y | 38673.6331829128 | 1.000000 | 38673.6331829128 |

## Bucket Mapping

GIRR bucket mapping uses currency, so selected USD GIRR sensitivities map to
the USD bucket. Equity uses the documented synthetic bucket 12 index assumption.
FX uses the exchange rate between the instrument currency and reporting
currency, so selected EUR/USD sensitivities map to `EUR/USD`.

## Parameter Provenance

Implemented parameters are recorded in `regulatory/parameter_crosswalk.csv`.
The selected configuration is `configs/sa/selected_sbm_parameters.yaml`. Every
implemented numeric regulatory parameter references BIS_MAR21 and a MAR21
paragraph or table.

## Weighted Sensitivity Preparation

Weighted sensitivity is calculated as:

```text
raw_sensitivity * risk_weight_decimal
```

The generated raw and weighted sensitivity artifact is
`data/artifacts/phase2_raw_sensitivities.csv`, which is ignored by default.

## Curvature Preparation

Curvature provenance is frozen as `VERIFIED_NOT_IMPLEMENTED`. Phase 2 does not
calculate CVR, curvature bucket capital, cross-bucket curvature aggregation or
scenario capital.

## Independent Numerical Checks

Tests cover finite-difference GIRR PV01, the expected sign for long fixed-rate
exposures, deterministic IRS sensitivity, analytical equity and FX delta checks,
central-difference option vega checks, regulatory vega transformation, maturity
allocation and weighted-sensitivity arithmetic.

## Explicitly Deferred Aggregation

No SBM capital result is produced in Phase 2. Deferred items include
within-bucket aggregation, cross-bucket aggregation, low/medium/high correlation
scenarios, curvature capital, DRC, RRAO, IMA, RFET, PLA and backtesting.

## Limitations

This is a selected educational implementation using synthetic instruments and
market inputs. It does not represent a complete Standardised Approach engine,
bank production model, legal/regulatory index classification or regulatory
filing artifact.
