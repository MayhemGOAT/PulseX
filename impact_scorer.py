"""Rule-based market impact scoring layered on FinBERT polarity."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

# High-impact keyword buckets — weight reflects typical market sensitivity.
HIGH_IMPACT_KEYWORDS: dict[str, float] = {
    # Monetary / Fed
    "rate hike": 1.0,
    "rate cut": 1.0,
    "interest rate": 0.9,
    "interest rates": 0.9,
    "fed funds": 0.9,
    "federal reserve": 0.85,
    "inflation": 0.85,
    "monetary policy": 0.85,
    "quantitative tightening": 0.9,
    "quantitative easing": 0.9,
    "basis points": 0.8,
    "higher for longer": 0.85,
    "hawkish": 0.8,
    "dovish": 0.75,
    "pivot": 0.75,
    # Macro / geopolitical
    "recession": 0.95,
    "gdp": 0.7,
    "unemployment": 0.75,
    "tariff": 0.9,
    "tariffs": 0.9,
    "trade war": 0.9,
    "sanctions": 0.85,
    "default": 0.9,
    "debt ceiling": 0.85,
    "stimulus": 0.8,
    "shutdown": 0.75,
    "geopolitical": 0.8,
    # Corporate / earnings
    "earnings": 0.85,
    "revenue": 0.75,
    "guidance": 0.8,
    "layoffs": 0.8,
    "layoff": 0.75,
    "bankruptcy": 0.95,
    "merger": 0.75,
    "acquisition": 0.7,
    "ipo": 0.7,
    "stock split": 0.65,
    "buyback": 0.65,
    # Market stress
    "crash": 0.95,
    "selloff": 0.85,
    "rally": 0.75,
    "volatility": 0.7,
    "bear market": 0.9,
    "bull market": 0.75,
}

BULLISH_TERMS = {
    "rate cut", "quantitative easing", "stimulus", "rally", "bull market",
    "buyback", "merger", "acquisition", "ipo", "stock split", "dovish",
}
BEARISH_TERMS = {
    "rate hike", "recession", "tariff", "tariffs", "trade war", "sanctions",
    "default", "debt ceiling", "layoffs", "layoff", "bankruptcy", "crash",
    "selloff", "bear market", "quantitative tightening", "higher for longer",
    "shutdown", "hawkish",
}

_SORTED_KEYWORDS = sorted(HIGH_IMPACT_KEYWORDS.keys(), key=len, reverse=True)
_KEYWORD_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in _SORTED_KEYWORDS),
    re.IGNORECASE,
)

TIER_THRESHOLDS = {"high": 0.55, "medium": 0.25}


def _match_keywords(text: str) -> list[str]:
    if not text:
        return []
    return list(dict.fromkeys(m.group(0).lower() for m in _KEYWORD_PATTERN.finditer(text)))


def _keyword_signal(matched: list[str]) -> tuple[float, float]:
    """Return (signed_signal, magnitude) in roughly [-1, 1]."""
    if not matched:
        return 0.0, 0.0

    weights = [HIGH_IMPACT_KEYWORDS.get(kw, 0.5) for kw in matched]
    magnitude = min(float(np.mean(weights)), 1.0)

    bull = sum(HIGH_IMPACT_KEYWORDS.get(kw, 0.5) for kw in matched if kw in BULLISH_TERMS)
    bear = sum(HIGH_IMPACT_KEYWORDS.get(kw, 0.5) for kw in matched if kw in BEARISH_TERMS)
    if bull > bear:
        signed = magnitude
    elif bear > bull:
        signed = -magnitude
    else:
        signed = 0.0

    return signed, magnitude


def _impact_tier(abs_score: float, keyword_count: int) -> str:
    if abs_score >= TIER_THRESHOLDS["high"] or keyword_count >= 3:
        return "high"
    if abs_score >= TIER_THRESHOLDS["medium"] or keyword_count >= 1:
        return "medium"
    return "low"


def score_market_impact(text: str, finbert_score: float) -> dict:
    """
    Hybrid rule + FinBERT market impact score.

    Returns impact_score (-1..1), impact_tier (low/medium/high), matched_keywords.
    """
    matched = _match_keywords(text)
    kw_signed, kw_magnitude = _keyword_signal(matched)
    finbert_score = float(np.clip(finbert_score, -1.0, 1.0))

    if kw_magnitude > 0:
        keyword_component = kw_signed if kw_signed != 0 else finbert_score * kw_magnitude
        impact_score = float(np.clip(0.45 * finbert_score + 0.55 * keyword_component, -1.0, 1.0))
        boost = 1.0 + 0.15 * min(len(matched), 3)
        impact_score = float(np.clip(impact_score * boost, -1.0, 1.0))
    else:
        impact_score = finbert_score * 0.6

    return {
        "impact_score": round(impact_score, 4),
        "impact_tier": _impact_tier(abs(impact_score), len(matched)),
        "matched_keywords": matched,
    }


def score_tweets_impact(tweets_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add impact_score, impact_tier, matched_keywords, impact_magnitude columns.

    Expects text and optionally sentiment_score (FinBERT polarity).
    """
    if tweets_df.empty:
        out = tweets_df.copy()
        for col, dtype in (
            ("impact_score", float),
            ("impact_tier", object),
            ("matched_keywords", object),
            ("impact_magnitude", float),
        ):
            out[col] = pd.Series(dtype=dtype)
        return out

    out = tweets_df.copy()
    finbert_col = "sentiment_score" if "sentiment_score" in out.columns else None

    impacts = []
    for _, row in out.iterrows():
        finbert = float(row[finbert_col]) if finbert_col else 0.0
        impacts.append(score_market_impact(str(row.get("text", "")), finbert))

    out["impact_score"] = [i["impact_score"] for i in impacts]
    out["impact_tier"] = [i["impact_tier"] for i in impacts]
    out["matched_keywords"] = [i["matched_keywords"] for i in impacts]
    out["impact_magnitude"] = out["impact_score"].abs()
    return out
