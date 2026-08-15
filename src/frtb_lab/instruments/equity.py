"""Equity instrument taxonomy records."""

from dataclasses import dataclass

from frtb_lab.instruments.base import Instrument


@dataclass(frozen=True)
class EquityIndex(Instrument):
    """Synthetic cash equity or ETF-style exposure."""


@dataclass(frozen=True)
class EquityOption(Instrument):
    """Synthetic vanilla European equity option."""


@dataclass(frozen=True)
class EquityBarrierOption(Instrument):
    """Synthetic path-dependent equity option for RRAO preparation."""
