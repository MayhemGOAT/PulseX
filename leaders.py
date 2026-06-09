"""Curated registry of market-moving X/Twitter accounts."""

from dataclasses import dataclass
from enum import Enum


class LeaderCategory(str, Enum):
    FED = "fed"
    CEO = "ceo"
    POLITICIAN = "politician"
    INFLUENCER = "influencer"
    MACRO = "macro"


@dataclass(frozen=True)
class Leader:
    handle: str
    name: str
    category: LeaderCategory
    weight: float  # influence weight for aggregate sentiment (0-1)
    tickers: tuple[str, ...]  # assets most affected by this voice


# Default watchlist — extend or override via config.
MARKET_LEADERS: list[Leader] = [
    Leader("elonmusk", "Elon Musk", LeaderCategory.CEO, 0.9, ("TSLA", "SPY")),
    Leader("JeromePowell", "Jerome Powell", LeaderCategory.FED, 1.0, ("SPY", "QQQ", "TLT")),
    Leader("federalreserve", "Federal Reserve", LeaderCategory.FED, 0.95, ("SPY", "TLT")),
    Leader("POTUS", "US President", LeaderCategory.POLITICIAN, 0.85, ("SPY",)),
    Leader("sundarpichai", "Sundar Pichai", LeaderCategory.CEO, 0.6, ("GOOGL",)),
    Leader("tim_cook", "Tim Cook", LeaderCategory.CEO, 0.7, ("AAPL",)),
    Leader("jimcramer", "Jim Cramer", LeaderCategory.INFLUENCER, 0.5, ("SPY",)),
    Leader("RayDalio", "Ray Dalio", LeaderCategory.MACRO, 0.75, ("SPY", "GLD")),
    Leader("chamath", "Chamath Palihapitiya", LeaderCategory.INFLUENCER, 0.55, ("SPY", "QQQ")),
]

LEADER_BY_HANDLE = {leader.handle.lower(): leader for leader in MARKET_LEADERS}


def get_leaders_for_ticker(ticker: str) -> list[Leader]:
    """Return leaders whose watchlist includes the ticker."""
    return [leader for leader in MARKET_LEADERS if ticker.upper() in leader.tickers]
