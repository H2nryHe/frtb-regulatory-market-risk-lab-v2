"""Credit instrument taxonomy records."""

from dataclasses import dataclass

from frtb_lab.instruments.base import Instrument


@dataclass(frozen=True)
class CorporateBond(Instrument):
    """Synthetic non-securitisation corporate bond for DRC preparation."""
