"""Rates instrument taxonomy records."""

from dataclasses import dataclass

from frtb_lab.instruments.base import Instrument


@dataclass(frozen=True)
class GovernmentBond(Instrument):
    """Synthetic government bond used for future GIRR mapping."""


@dataclass(frozen=True)
class InterestRateSwap(Instrument):
    """Synthetic vanilla interest-rate swap used for future GIRR mapping."""
