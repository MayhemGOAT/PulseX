"""Tests for impact scorer and event detector."""

import pandas as pd

from event_detector import detect_events, get_event_days
from impact_scorer import score_market_impact, score_tweets_impact


def test_bullish_keywords_score_positive():
    result = score_market_impact("Markets rally on strong earnings beat", 0.1)
    assert result["impact_score"] > 0
    assert result["impact_tier"] in {"medium", "high"}


def test_bearish_keywords_score_negative():
    result = score_market_impact("Recession fears grow after rate hike warning", -0.1)
    assert result["impact_score"] < 0


def test_score_tweets_impact_adds_columns():
    df = pd.DataFrame({
        "text": ["Rate hike coming", "Markets rally"],
        "sentiment_score": [0.0, 0.2],
        "handle": ["JeromePowell", "elonmusk"],
    })
    scored = score_tweets_impact(df)
    assert "impact_score" in scored.columns
    assert "impact_tier" in scored.columns


def test_detect_tier1_events():
    df = pd.DataFrame({
        "handle": ["JeromePowell", "jimcramer"],
        "text": ["Rate hike at next meeting", "Buy the dip"],
        "created_at": pd.to_datetime(["2024-03-15", "2024-03-15"], utc=True),
        "sentiment_score": [-0.3, 0.2],
        "impact_score": [-0.4, 0.1],
        "impact_tier": ["high", "low"],
    })
    events = detect_events(df, min_weight=0.85)
    assert len(events) >= 1
    assert events[0].leader == "JeromePowell"
