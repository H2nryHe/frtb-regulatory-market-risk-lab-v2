"""Lightweight Phase 1 instrument taxonomy."""

from frtb_lab.instruments.base import Instrument, InstrumentValidationError
from frtb_lab.instruments.credit import CorporateBond
from frtb_lab.instruments.equity import EquityBarrierOption, EquityIndex, EquityOption
from frtb_lab.instruments.fx import FxForward, FxOption
from frtb_lab.instruments.rates import GovernmentBond, InterestRateSwap

__all__ = [
    "CorporateBond",
    "EquityBarrierOption",
    "EquityIndex",
    "EquityOption",
    "FxForward",
    "FxOption",
    "GovernmentBond",
    "Instrument",
    "InstrumentValidationError",
    "InterestRateSwap",
]
