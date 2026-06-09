"""Event-driven signal detection from scored leader tweets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from leaders import LEADER_BY_HANDLE, LeaderCategory
from impact_scorer import score_tweets_impact

# Map leader categories to event_type labels used in backtests.
_CATEGORY_TO_EVENT_TYPE: dict[LeaderCategory, str] = {
    LeaderCategory.FED: "fed",
    LeaderCategory.CEO: "ceo",
    LeaderCategory.POLITICIAN: "politician",
    LeaderCategory.INFLUENCER: "influencer",
    LeaderCategory.MACRO: "macro",
}

# Minimum absolute impact for tier-high fallback when tier column missing.
TIER_HIGH_MAGNITUDE = 0.55


@dataclass
class MarketEvent:
    date: date
    leader: str
    text: str
    impact_score: float
    event_type: str


def _resolve_event_type(handle: str) -> str:
    leader = LEADER_BY_HANDLE.get(str(handle).lower())
    if leader is None:
        return "unknown"
    return _CATEGORY_TO_EVENT_TYPE.get(leader.category, "unknown")


def _leader_weight(handle: str) -> float:
    leader = LEADER_BY_HANDLE.get(str(handle).lower())
    return leader.weight if leader else 0.5


def _ensure_impact_columns(scored_tweets: pd.DataFrame) -> pd.DataFrame:
    if "impact_score" not in scored_tweets.columns:
        return score_tweets_impact(scored_tweets)
    return scored_tweets


def detect_events(
    scored_tweets: pd.DataFrame,
    min_weight: float = 0.85,
) -> list[MarketEvent]:
    """
    Detect high-impact market events from scored tweets.

    Filters by leader weight and impact tier/score.
    """
    if scored_tweets.empty:
        return []

    tweets = _ensure_impact_columns(scored_tweets).copy()
    tweets["leader_weight"] = tweets["handle"].map(_leader_weight)
    tweets["event_date"] = pd.to_datetime(tweets["created_at"]).dt.date

    if "impact_tier" not in tweets.columns:
        tweets["impact_tier"] = "low"
    magnitude = (
        tweets["impact_magnitude"]
        if "impact_magnitude" in tweets.columns
        else tweets["impact_score"].abs()
    )

    mask = (
        (tweets["leader_weight"] >= min_weight)
        & ((tweets["impact_tier"] == "high") | (magnitude >= TIER_HIGH_MAGNITUDE))
    )
    candidates = tweets.loc[mask].sort_values("created_at")

    events: list[MarketEvent] = []
    for _, row in candidates.iterrows():
        events.append(
            MarketEvent(
                date=row["event_date"],
                leader=str(row["handle"]),
                text=str(row["text"]),
                impact_score=float(row["impact_score"]),
                event_type=_resolve_event_type(str(row["handle"])),
            )
        )
    return events


def get_event_days(scored_tweets: pd.DataFrame, min_weight: float = 0.85) -> set[date]:
    """Return calendar dates with at least one high-impact event."""
    events = detect_events(scored_tweets, min_weight=min_weight)
    return {event.date for event in events}


def filter_event_periods(prices_df: pd.DataFrame, event_days: set[date]) -> pd.DataFrame:
    """
    Restrict price history to rows on event days (for event-only backtesting).

    Uses normalized index dates; returns empty frame if no overlap.
    """
    if prices_df.empty or not event_days:
        return prices_df.iloc[0:0].copy()

    index_dates = pd.to_datetime(prices_df.index).normalize().date
    mask = pd.Series(index_dates, index=prices_df.index).isin(event_days)
    return prices_df.loc[mask].copy()
