"""Council orchestrator — weighted deliberation across specialist members."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from council.base import CouncilContext, CouncilMember, MemberOpinion
from council.members import DEFAULT_MEMBERS


@dataclass
class CouncilVerdict:
    """Aggregated council decision for a single trading day."""

    direction: float  # -1 to 1
    confidence: float  # 0 to 1
    consensus_strength: float  # 0 to 1, agreement among members
    member_opinions: list[MemberOpinion] = field(default_factory=list)
    reasoning: str = ""


def _normalize_date(value: date | pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def _tweets_for_date(tweets: pd.DataFrame, day: date | pd.Timestamp) -> pd.DataFrame:
    if tweets.empty or "created_at" not in tweets.columns:
        return tweets.iloc[0:0].copy()

    target = _normalize_date(day)
    dates = pd.to_datetime(tweets["created_at"]).dt.normalize()
    return tweets.loc[dates == target].copy()


class Council:
    """Runs specialist members and produces a weighted market verdict."""

    def __init__(
        self,
        members: list[CouncilMember] | None = None,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.members = members if members is not None else list(DEFAULT_MEMBERS)
        if weights:
            for member in self.members:
                if member.name in weights:
                    member.weight = float(weights[member.name])

    def deliberate(self, context: CouncilContext) -> CouncilVerdict:
        opinions = [member.analyze(context) for member in self.members]

        total_weight = sum(member.weight for member in self.members)
        if total_weight == 0:
            return CouncilVerdict(
                direction=0.0,
                confidence=0.0,
                consensus_strength=0.0,
                member_opinions=opinions,
                reasoning="No council members configured.",
            )

        weighted_dir = sum(
            op.direction * op.confidence * member.weight
            for op, member in zip(opinions, self.members)
        ) / total_weight

        weighted_conf = sum(
            op.confidence * member.weight for op, member in zip(opinions, self.members)
        ) / total_weight

        directions = np.array([op.direction for op in opinions])
        consensus = 1.0 - float(np.std(directions)) if len(directions) > 1 else 1.0
        consensus = max(0.0, min(1.0, consensus))

        label = "BULLISH" if weighted_dir > 0.05 else "BEARISH" if weighted_dir < -0.05 else "NEUTRAL"
        summary = (
            f"Council {label} (dir {weighted_dir:+.3f}, conf {weighted_conf:.2f}, "
            f"consensus {consensus:.2f}). "
            + "; ".join(f"{op.member_name}: {op.reasoning}" for op in opinions)
        )

        return CouncilVerdict(
            direction=max(-1.0, min(1.0, weighted_dir)),
            confidence=max(0.0, min(1.0, weighted_conf)),
            consensus_strength=consensus,
            member_opinions=opinions,
            reasoning=summary,
        )

    def predict_market(
        self,
        prices: pd.DataFrame,
        tweets: pd.DataFrame,
        ticker: str,
        as_of: date | pd.Timestamp | None = None,
    ) -> dict:
        """Deliberate on the latest (or specified) trading day."""
        if prices.empty:
            raise ValueError("prices DataFrame is empty")

        idx = prices.index[-1] if as_of is None else as_of
        if idx not in prices.index:
            idx = prices.index[prices.index.get_indexer([idx], method="pad")[0]]

        price_row = prices.loc[idx]
        day = _normalize_date(idx)
        day_tweets = _tweets_for_date(tweets, day)

        context = CouncilContext(
            price_row=price_row,
            tweets=day_tweets,
            ticker=ticker.upper(),
            date=day,
        )
        verdict = self.deliberate(context)

        direction_label = "UP" if verdict.direction > 0.05 else "DOWN" if verdict.direction < -0.05 else "FLAT"

        return {
            "ticker": ticker.upper(),
            "date": str(day.date()),
            "direction": direction_label,
            "council_label": direction_label,
            "direction_score": round(verdict.direction, 4),
            "council_direction": round(verdict.direction, 4),
            "confidence": round(verdict.confidence, 4),
            "council_confidence": round(verdict.confidence, 4),
            "consensus_strength": round(verdict.consensus_strength, 4),
            "reasoning": verdict.reasoning,
            "summary": verdict.reasoning,
            "verdict": verdict,
            "members": [
                {
                    "name": op.member_name,
                    "direction": round(op.direction, 4),
                    "confidence": round(op.confidence, 4),
                    "reasoning": op.reasoning,
                    "signals": op.signals,
                }
                for op in verdict.member_opinions
            ],
            "member_opinions": [
                {
                    "name": op.member_name,
                    "direction": round(op.direction, 4),
                    "confidence": round(op.confidence, 4),
                    "reasoning": op.reasoning,
                    "signals": op.signals,
                }
                for op in verdict.member_opinions
            ],
        }
