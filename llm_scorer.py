"""Optional LLM market impact scorer with rule-based fallback.

Optional dependency (not required): openai>=1.0.0
Set OPENAI_API_KEY to enable future LLM scoring; currently uses enhanced rules.
"""

from __future__ import annotations

import os
import re

import pandas as pd

from impact_scorer import score_market_impact
from leaders import LEADER_BY_HANDLE

_TICKER_RE = re.compile(r"\$([A-Z]{1,5})\b")


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


def _build_reasoning(text: str, impact: float, matched: list[str], leader_handle: str) -> str:
    direction = "bullish" if impact > 0.05 else "bearish" if impact < -0.05 else "neutral"
    hits = ", ".join(matched[:4]) if matched else "general market commentary"
    leader = LEADER_BY_HANDLE.get(leader_handle.lower())
    source = leader.name if leader else leader_handle
    return f"{source}: {direction} signal ({impact:+.2f}) — keywords: {hits}"


class LLMImpactScorer:
    """Score tweet market impact; uses rules today, LLM when wired with openai."""

    def __init__(self) -> None:
        self._use_llm = bool(os.getenv("OPENAI_API_KEY"))

    def score(self, text: str, leader_handle: str) -> dict:
        finbert_hint = 0.0
        base = score_market_impact(text, finbert_hint)
        impact = base["impact_score"]
        matched = base["matched_keywords"]

        if self._use_llm:
            # Stub: enhanced rule-based until openai client is integrated.
            impact = max(-1.0, min(1.0, impact * 1.05))

        return {
            "market_impact": round(impact, 4),
            "reasoning": _build_reasoning(text, impact, matched, leader_handle),
            "affected_tickers": _extract_tickers(text, leader_handle),
            "urgency": _urgency_from_impact(impact, base["impact_tier"]),
        }


def score_tweets_llm(tweets_df: pd.DataFrame) -> pd.DataFrame:
    """Add LLM/rule-based impact columns to scored tweets."""
    if tweets_df.empty:
        return tweets_df

    scorer = LLMImpactScorer()
    out = tweets_df.copy()
    results = [
        scorer.score(str(row["text"]), str(row.get("handle", "")))
        for _, row in out.iterrows()
    ]
    out["llm_market_impact"] = [r["market_impact"] for r in results]
    out["llm_reasoning"] = [r["reasoning"] for r in results]
    out["llm_affected_tickers"] = [r["affected_tickers"] for r in results]
    out["llm_urgency"] = [r["urgency"] for r in results]
    return out
