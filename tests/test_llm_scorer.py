"""Tests for LLM impact scorer."""

import os

import pandas as pd

from llm_scorer import LLMImpactScorer, score_tweets_llm


def test_score_returns_expected_keys():
    scorer = LLMImpactScorer()
    result = scorer.score("Rate hike coming", "JeromePowell")
    assert -1 <= result["market_impact"] <= 1
    assert result["urgency"] in {"low", "medium", "high"}
    assert "SPY" in result["affected_tickers"]
    assert result["reasoning"]
    assert result.get("source") == "rules"


def test_score_tweets_llm_adds_columns():
    df = pd.DataFrame({
        "text": ["Markets rally on rate cut", "Tesla $TSLA production beat"],
        "handle": ["JeromePowell", "elonmusk"],
        "sentiment_score": [0.1, 0.3],
    })
    scored = score_tweets_llm(df)
    for col in ("llm_market_impact", "llm_reasoning", "llm_affected_tickers", "llm_urgency"):
        assert col in scored.columns


def test_pulsex_llm_integration():
    os.environ["PULSEX_FAST"] = "1"
    os.environ["PULSEX_LLM"] = "1"
    from pulse_x import prepare_dataset, TICKER

    _, tweets = prepare_dataset(TICKER)
    if not tweets.empty:
        assert "llm_market_impact" in tweets.columns
