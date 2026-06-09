"""Base types for the PulseX AI Council."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

import pandas as pd


@dataclass
class CouncilContext:
    """Inputs available to each council member for a single trading day."""

    price_row: pd.Series
    tweets: pd.DataFrame
    ticker: str
    date: date | pd.Timestamp


@dataclass
class MemberOpinion:
    """One specialist's view on market direction."""

    direction: float  # -1 (bearish) to 1 (bullish)
    confidence: float  # 0 to 1
    reasoning: str
    signals: dict = field(default_factory=dict)
    member_name: str = ""


@dataclass
class CouncilMember(ABC):
    """Specialist agent that analyzes context and returns an opinion."""

    name: str
    role: str
    weight: float

    @abstractmethod
    def analyze(self, context: CouncilContext) -> MemberOpinion:
        """Return directional opinion for the given context."""
