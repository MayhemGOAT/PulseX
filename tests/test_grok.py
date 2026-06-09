"""Tests for Grok integration."""

from unittest.mock import patch

from grok_client import _parse_json_content, is_available
from llm_scorer import LLMImpactScorer, grok_enabled, score_tweets_llm


def test_parse_json_from_fenced_response():
    raw = '```json\n{"market_impact": 0.5, "reasoning": "bullish"}\n```'
    parsed = _parse_json_content(raw)
    assert parsed["market_impact"] == 0.5


def test_rule_fallback_without_api_key():
    scorer = LLMImpactScorer(use_grok=False)
    result = scorer.score("Rate hike coming soon", "JeromePowell")
    assert -1 <= result["market_impact"] <= 1
    assert result["source"] == "rules"


@patch("llm_scorer.is_available", return_value=True)
@patch("llm_scorer.score_tweet_impact")
def test_grok_scoring_when_available(mock_score, _mock_avail):
    mock_score.return_value = {
        "market_impact": 0.6,
        "reasoning": "Dovish Fed tone",
        "affected_tickers": ["SPY"],
        "urgency": "high",
    }
    scorer = LLMImpactScorer(use_grok=True)
    result = scorer.score("Rate cut likely", "JeromePowell")
    assert result["market_impact"] == 0.6
    assert result["source"] == "grok"


def test_grok_enabled_respects_env(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("PULSEX_GROK", "0")
    assert grok_enabled() is False
    monkeypatch.setenv("PULSEX_GROK", "1")
    assert grok_enabled() is True
