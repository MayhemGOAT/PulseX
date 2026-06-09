"""Score tweet text with FinBERT and build daily leader-sentiment features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from leaders import LEADER_BY_HANDLE, Leader

_finbert_pipeline = None


def _get_finbert():
    global _finbert_pipeline
    if _finbert_pipeline is None:
        from transformers import pipeline

        _finbert_pipeline = pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            top_k=None,
        )
    return _finbert_pipeline


def score_text(text: str) -> dict[str, float]:
    """Return FinBERT probabilities for positive/negative/neutral."""
    import os
    if os.getenv("PULSEX_FAST") == "1":
        return _score_text_fast(text)
    pipe = _get_finbert()
    scores = pipe(text[:512])[0]
    result = {item["label"].lower(): item["score"] for item in scores}
    return {
        "positive": result.get("positive", 0.0),
        "negative": result.get("negative", 0.0),
        "neutral": result.get("neutral", 0.0),
        "score": result.get("positive", 0.0) - result.get("negative", 0.0),
    }


def _score_text_fast(text: str) -> dict[str, float]:
    """Keyword-only fast scoring for tests/CI (no FinBERT download)."""
    from impact_scorer import score_market_impact
    impact = score_market_impact(text, 0.0)
    s = impact["impact_score"]
    pos = max(s, 0)
    neg = max(-s, 0)
    neu = 1.0 - pos - neg
    return {"positive": pos, "negative": neg, "neutral": max(neu, 0), "score": s}


def score_tweets(tweets_df: pd.DataFrame) -> pd.DataFrame:
    """Add sentiment columns to a tweets DataFrame."""
    if tweets_df.empty:
        return tweets_df

    scored = tweets_df.copy()
    sentiments = [score_text(text) for text in scored["text"]]
    for key in ("positive", "negative", "neutral", "score"):
        scored[f"sentiment_{key}"] = [s[key] for s in sentiments]

    scored["leader_weight"] = scored["handle"].str.lower().map(
        lambda h: LEADER_BY_HANDLE[h].weight if h in LEADER_BY_HANDLE else 0.5
    )
    scored["weighted_score"] = scored["sentiment_score"] * scored["leader_weight"]
    return scored


def _engagement_boost(row: pd.Series) -> float:
    """Light engagement multiplier — viral posts weigh more."""
    engagement = row.get("like_count", 0) + row.get("retweet_count", 0) * 2
    return 1.0 + min(np.log1p(engagement) / 10.0, 0.5)


def build_daily_sentiment(
    scored_tweets: pd.DataFrame,
    price_index: pd.DatetimeIndex,
) -> pd.DataFrame:
    """
    Aggregate leader tweets into daily features aligned to trading days.

    Tweets posted after market close are attributed to the next trading day.
    """
    if scored_tweets.empty:
        index = price_index.normalize().unique()
        empty = pd.DataFrame(index=index)
        for col in _sentiment_feature_names():
            empty[col] = 0.0
        return empty

    tweets = scored_tweets.copy()
    tweets["date"] = tweets["created_at"].dt.normalize()
    tweets["engagement_boost"] = tweets.apply(_engagement_boost, axis=1)
    tweets["final_score"] = tweets["weighted_score"] * tweets["engagement_boost"]

    daily = (
        tweets.groupby("date")
        .agg(
            leader_sentiment=("final_score", "mean"),
            leader_sentiment_max=("final_score", "max"),
            leader_sentiment_min=("final_score", "min"),
            tweet_count=("tweet_id", "count"),
            bullish_tweets=("sentiment_score", lambda s: (s > 0.15).sum()),
            bearish_tweets=("sentiment_score", lambda s: (s < -0.15).sum()),
            avg_engagement=("engagement_boost", "mean"),
        )
        .reindex(price_index.normalize().unique())
        .fillna(0)
    )

    daily["leader_sentiment_ma5"] = daily["leader_sentiment"].rolling(5, min_periods=1).mean()
    daily["leader_sentiment_ma20"] = daily["leader_sentiment"].rolling(20, min_periods=1).mean()
    daily["leader_momentum_5"] = daily["leader_sentiment"] - daily["leader_sentiment"].shift(5)
    daily["leader_volatility_10"] = daily["leader_sentiment"].rolling(10, min_periods=1).std().fillna(0)
    daily["leader_bullish_ratio"] = np.where(
        daily["tweet_count"] > 0,
        daily["bullish_tweets"] / daily["tweet_count"],
        0,
    )

    return daily


def _sentiment_feature_names() -> list[str]:
    return [
        "leader_sentiment",
        "leader_sentiment_max",
        "leader_sentiment_min",
        "tweet_count",
        "bullish_tweets",
        "bearish_tweets",
        "avg_engagement",
        "leader_sentiment_ma5",
        "leader_sentiment_ma20",
        "leader_momentum_5",
        "leader_volatility_10",
        "leader_bullish_ratio",
    ]


def add_sentiment_to_prices(price_df: pd.DataFrame, tweets_df: pd.DataFrame) -> pd.DataFrame:
    """Merge daily leader sentiment features into OHLCV dataframe."""
    scored = score_tweets(tweets_df)
    sentiment = build_daily_sentiment(scored, price_df.index)
    merged = price_df.join(sentiment, how="left").fillna(0)
    return merged
