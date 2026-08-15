"""FX instrument taxonomy records."""

from dataclasses import dataclass

from frtb_lab.instruments.base import Instrument


@dataclass(frozen=True)
class FxForward(Instrument):
    """Synthetic FX forward used for future FX mapping."""


@dataclass(frozen=True)
class FxOption(Instrument):
    """Synthetic vanilla FX option used for future FX mapping."""
