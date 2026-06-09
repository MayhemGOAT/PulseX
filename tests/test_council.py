"""Tests for AI Council."""

import pandas as pd

from council import Council
from council.base import CouncilContext


def _make_context(
    sentiment: float = 0.2,
    tweet_count: int = 3,
    rsi: float = 45,
    tweets: pd.DataFrame | None = None,
) -> CouncilContext:
    row = pd.Series({
        "leader_sentiment": sentiment,
        "tweet_count": tweet_count,
        "bullish_tweets": 2,
        "bearish_tweets": 0,
        "leader_volatility_10": 0.1,
        "high_low_range": 0.01,
        "return_1d": 0.005,
        "rsi_14": rsi,
        "macd": 0.01,
        "macd_signal": 0.005,
        "sma_5_ratio": 0.01,
        "sma_20_ratio": 0.01,
        "sma_50_ratio": 0.01,
    })
    return CouncilContext(
        ticker="SPY",
        date=pd.Timestamp("2024-03-15"),
        price_row=row,
        tweets=tweets if tweets is not None else pd.DataFrame(),
    )


def test_council_deliberation_returns_verdict():
    council = Council()
    verdict = council.deliberate(_make_context())
    assert -1 <= verdict.direction <= 1
    assert 0 <= verdict.confidence <= 1
    assert len(verdict.member_opinions) == 6


def test_bullish_sentiment_skews_direction():
    council = Council()
    bullish = council.deliberate(_make_context(sentiment=0.5, tweet_count=5))
    neutral = council.deliberate(_make_context(sentiment=0.0, tweet_count=0))
    assert bullish.direction >= neutral.direction


def test_tier1_event_boosts_confidence():
    tweets = pd.DataFrame([{
        "handle": "JeromePowell",
        "text": "Rate cut coming soon",
        "created_at": "2024-03-15",
        "impact_score": 0.4,
        "sentiment_score": 0.4,
    }])
    council = Council()
    with_event = council.deliberate(_make_context(tweets=tweets))
    event_op = next(o for o in with_event.member_opinions if o.member_name == "Event Detector")
    assert event_op.confidence > 0.4
    assert event_op.signals.get("event_detected") is True
