"""Grok-powered market impact scoring with rule-based fallback."""

from __future__ import annotations

import os
import re

import pandas as pd

from grok_client import is_available, score_tweet_impact
from impact_scorer import score_market_impact
from leaders import LEADER_BY_HANDLE

_TICKER_RE = re.compile(r"\$([A-Z]{1,5})\b")


def grok_enabled() -> bool:
    """True when Grok scoring should run (API key or explicit flag)."""
    if os.getenv("PULSEX_GROK") == "0":
        return False
    if os.getenv("PULSEX_GROK") == "1" or os.getenv("PULSEX_LLM") == "1":
        return True
    return is_available()


def _extract_tickers(text: str, leader_handle: str) -> list[str]:
    tickers = set(_TICKER_RE.findall(text.upper()))
    leader = LEADER_BY_HANDLE.get(leader_handle.lower())
    if leader:
        tickers.update(leader.tickers)
    return sorted(tickers)


def _urgency_from_impact(impact: float, tier: str) -> str:
    if tier == "high" or abs(impact) >= 0.5:
        return "high"
    if tier == "medium" or abs(impact) >= 0.2:
        return "medium"
    return "low"


def _rule_score(text: str, leader_handle: str) -> dict:
    base = score_market_impact(text, 0.0)
    impact = base["impact_score"]
    matched = base["matched_keywords"]
    leader = LEADER_BY_HANDLE.get(leader_handle.lower())
    source = leader.name if leader else leader_handle
    direction = "bullish" if impact > 0.05 else "bearish" if impact < -0.05 else "neutral"
    hits = ", ".join(matched[:4]) if matched else "general market commentary"
    return {
        "market_impact": round(impact, 4),
        "reasoning": f"{source}: {direction} signal ({impact:+.2f}) — keywords: {hits}",
        "affected_tickers": _extract_tickers(text, leader_handle),
        "urgency": _urgency_from_impact(impact, base["impact_tier"]),
        "source": "rules",
    }


class LLMImpactScorer:
    """Score tweet market impact via Grok (xAI), falling back to keyword rules."""

    def __init__(self, ticker: str = "SPY", use_grok: bool | None = None) -> None:
        self.ticker = ticker
        self.use_grok = grok_enabled() if use_grok is None else use_grok

    def score(self, text: str, leader_handle: str) -> dict:
        leader = LEADER_BY_HANDLE.get(leader_handle.lower())
        leader_name = leader.name if leader else leader_handle

        if self.use_grok and is_available():
            grok = score_tweet_impact(text, leader_handle, leader_name, self.ticker)
            if grok and "market_impact" in grok:
                return {
                    "market_impact": round(float(grok["market_impact"]), 4),
                    "reasoning": grok.get("reasoning", "Grok analysis"),
                    "affected_tickers": grok.get("affected_tickers") or _extract_tickers(text, leader_handle),
                    "urgency": grok.get("urgency", "medium"),
                    "source": "grok",
                }

        return _rule_score(text, leader_handle)


def score_tweets_llm(tweets_df: pd.DataFrame, ticker: str = "SPY") -> pd.DataFrame:
    """Add Grok/rule-based impact columns to scored tweets."""
    if tweets_df.empty:
        return tweets_df

    scorer = LLMImpactScorer(ticker=ticker)
    out = tweets_df.copy()
    results = [
        scorer.score(str(row["text"]), str(row.get("handle", "")))
        for _, row in out.iterrows()
    ]
    out["llm_market_impact"] = [r["market_impact"] for r in results]
    out["llm_reasoning"] = [r["reasoning"] for r in results]
    out["llm_affected_tickers"] = [r["affected_tickers"] for r in results]
    out["llm_urgency"] = [r["urgency"] for r in results]
    out["llm_source"] = [r.get("source", "rules") for r in results]
    return out
