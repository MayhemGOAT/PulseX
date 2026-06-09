"""Specialist council members — sentiment, technicals, macro, risk, events."""

from __future__ import annotations

import numpy as np
import pandas as pd

from leaders import LEADER_BY_HANDLE, LeaderCategory
from council.base import CouncilContext, CouncilMember, MemberOpinion

TIER1_WEIGHT = 0.85
MACRO_CATEGORIES = {LeaderCategory.FED, LeaderCategory.POLITICIAN}


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _row_val(row: pd.Series, key: str, default: float = 0.0) -> float:
    val = row.get(key, default)
    if pd.isna(val):
        return default
    return float(val)


class SentimentAnalyst(CouncilMember):
    """Aggregates leader tweet sentiment into a directional view."""

    def __init__(self) -> None:
        super().__init__(name="Sentiment Analyst", role="sentiment", weight=1.0)

    def analyze(self, context: CouncilContext) -> MemberOpinion:
        row = context.price_row
        sentiment = _row_val(row, "leader_sentiment")
        bullish = _row_val(row, "bullish_tweets")
        bearish = _row_val(row, "bearish_tweets")
        tweet_count = _row_val(row, "tweet_count")

        direction = _clip(np.tanh(sentiment * 3), -1, 1)

        if tweet_count > 0:
            net_bias = (bullish - bearish) / tweet_count
            direction = _clip(direction * 0.6 + net_bias * 0.4, -1, 1)

        confidence = _clip(min(tweet_count / 5, 1.0) * (0.4 + abs(sentiment)), 0, 1)
        reasoning = (
            f"Leader sentiment {sentiment:+.3f} with {int(bullish)} bullish / "
            f"{int(bearish)} bearish tweets ({int(tweet_count)} total)."
        )

        return MemberOpinion(
            direction=direction,
            confidence=confidence,
            reasoning=reasoning,
            signals={
                "leader_sentiment": sentiment,
                "bullish_tweets": bullish,
                "bearish_tweets": bearish,
                "tweet_count": tweet_count,
            },
            member_name=self.name,
        )


class TechnicalAnalyst(CouncilMember):
    """Reads RSI, MACD, and SMA ratios from the price feature row."""

    def __init__(self) -> None:
        super().__init__(name="Technical Analyst", role="technical", weight=0.9)

    def analyze(self, context: CouncilContext) -> MemberOpinion:
        row = context.price_row
        rsi = _row_val(row, "rsi_14", 50.0)
        macd = _row_val(row, "macd")
        macd_signal = _row_val(row, "macd_signal")
        sma5 = _row_val(row, "sma_5_ratio")
        sma20 = _row_val(row, "sma_20_ratio")
        sma50 = _row_val(row, "sma_50_ratio")

        rsi_signal = _clip((50 - rsi) / 30, -1, 1)
        macd_signal_dir = _clip(np.tanh((macd - macd_signal) * 50), -1, 1)
        sma_signal = _clip(np.tanh((sma5 + sma20 + sma50) / 3 * 10), -1, 1)

        direction = _clip(rsi_signal * 0.35 + macd_signal_dir * 0.35 + sma_signal * 0.30, -1, 1)
        confidence = _clip(0.5 + abs(direction) * 0.4, 0, 1)

        reasoning = (
            f"RSI {rsi:.1f}, MACD spread {(macd - macd_signal):+.4f}, "
            f"SMA ratios {sma5:+.3f}/{sma20:+.3f}/{sma50:+.3f}."
        )

        return MemberOpinion(
            direction=direction,
            confidence=confidence,
            reasoning=reasoning,
            signals={
                "rsi_14": rsi,
                "macd": macd,
                "macd_signal": macd_signal,
                "sma_5_ratio": sma5,
                "sma_20_ratio": sma20,
                "sma_50_ratio": sma50,
            },
            member_name=self.name,
        )


class MacroStrategist(CouncilMember):
    """Weights Fed and political leader voices more heavily."""

    def __init__(self) -> None:
        super().__init__(name="Macro Strategist", role="macro", weight=1.1)

    def analyze(self, context: CouncilContext) -> MemberOpinion:
        tweets = context.tweets
        macro_scores: list[float] = []
        macro_weights: list[float] = []

        if not tweets.empty and "handle" in tweets.columns:
            for _, tweet in tweets.iterrows():
                handle = str(tweet.get("handle", "")).lower()
                leader = LEADER_BY_HANDLE.get(handle)
                if leader is None or leader.category not in MACRO_CATEGORIES:
                    continue

                score = _row_val(tweet, "sentiment_score")
                if score == 0.0 and "sentiment_score" not in tweet.index:
                    score = _row_val(tweet, "weighted_score")

                weight = leader.weight * (1.5 if leader.category == LeaderCategory.FED else 1.2)
                macro_scores.append(score)
                macro_weights.append(weight)

        if macro_weights:
            direction = _clip(
                np.average(macro_scores, weights=macro_weights) if macro_scores else 0.0,
                -1,
                1,
            )
            direction = _clip(np.tanh(direction * 4), -1, 1)
            confidence = _clip(min(len(macro_weights) / 3, 1.0) * 0.8, 0, 1)
            reasoning = (
                f"Fed/political macro voices ({len(macro_weights)} posts) "
                f"weighted avg sentiment {direction:+.3f}."
            )
        else:
            fallback = _row_val(context.price_row, "leader_sentiment")
            direction = _clip(np.tanh(fallback * 2), -1, 1)
            confidence = 0.25
            reasoning = "No Fed/political tweets today; using aggregate leader sentiment as proxy."

        return MemberOpinion(
            direction=direction,
            confidence=confidence,
            reasoning=reasoning,
            signals={
                "macro_tweet_count": len(macro_weights),
                "macro_direction": direction,
            },
            member_name=self.name,
        )


class RiskManager(CouncilMember):
    """Dampens conviction when sentiment or price volatility is elevated."""

    def __init__(self) -> None:
        super().__init__(name="Risk Manager", role="risk", weight=0.8)

    def analyze(self, context: CouncilContext) -> MemberOpinion:
        row = context.price_row
        vol = _row_val(row, "leader_volatility_10")
        hl_range = _row_val(row, "high_low_range")
        sentiment = _row_val(row, "leader_sentiment")

        vol_stress = _clip(vol * 5 + hl_range * 10, 0, 1)
        direction = _clip(np.tanh(sentiment * 2), -1, 1)

        if vol_stress > 0.6:
            direction *= 1 - (vol_stress - 0.6)

        confidence = _clip(1.0 - vol_stress, 0, 1)
        reasoning = (
            f"Volatility stress {vol_stress:.2f} "
            f"(sentiment vol {vol:.3f}, high-low range {hl_range:.3f})."
        )

        return MemberOpinion(
            direction=direction,
            confidence=confidence,
            reasoning=reasoning,
            signals={
                "leader_volatility_10": vol,
                "high_low_range": hl_range,
                "vol_stress": vol_stress,
            },
            member_name=self.name,
        )


class EventDetector(CouncilMember):
    """Flags tier-1 leader activity and amplifies event-day signals."""

    def __init__(self) -> None:
        super().__init__(name="Event Detector", role="events", weight=1.0)

    def analyze(self, context: CouncilContext) -> MemberOpinion:
        tweets = context.tweets
        tier1_handles = {h for h, leader in LEADER_BY_HANDLE.items() if leader.weight >= TIER1_WEIGHT}
        active: list[str] = []

        if not tweets.empty and "handle" in tweets.columns:
            for handle in tweets["handle"].str.lower().unique():
                if handle in tier1_handles:
                    active.append(handle)

        if not active:
            return MemberOpinion(
                direction=0.0,
                confidence=0.1,
                reasoning="No tier-1 leader posts today.",
                signals={"tier1_active": [], "event_detected": False},
                member_name=self.name,
            )

        scores: list[float] = []
        for _, tweet in tweets.iterrows():
            handle = str(tweet.get("handle", "")).lower()
            if handle not in tier1_handles:
                continue
            score = _row_val(tweet, "sentiment_score")
            if score == 0.0 and "sentiment_score" not in tweet.index:
                score = _row_val(tweet, "weighted_score")
            leader = LEADER_BY_HANDLE[handle]
            scores.append(score * leader.weight)

        raw = float(np.mean(scores)) if scores else 0.0
        direction = _clip(np.tanh(raw * 5), -1, 1)
        boost = 1.0 + 0.3 * len(active)
        direction = _clip(direction * boost, -1, 1)
        confidence = _clip(min(len(active) / 2, 1.0) * 0.9, 0, 1)

        names = [LEADER_BY_HANDLE[h].name for h in active]
        reasoning = f"Tier-1 event: {', '.join(names)} posted today (boost {boost:.1f}x)."

        return MemberOpinion(
            direction=direction,
            confidence=confidence,
            reasoning=reasoning,
            signals={
                "tier1_active": active,
                "event_detected": True,
                "event_boost": boost,
            },
            member_name=self.name,
        )


DEFAULT_MEMBERS: list[CouncilMember] = [
    SentimentAnalyst(),
    TechnicalAnalyst(),
    MacroStrategist(),
    RiskManager(),
    EventDetector(),
]
