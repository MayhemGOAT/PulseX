"""Local market judge — scores Grok paste + price data into predictions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import yfinance as yf

from grok_bridge.parser import GrokBriefing, TickerSignal


@dataclass
class StockPrediction:
    ticker: str
    direction: str       # UP / DOWN / FLAT
    confidence: float    # 0-1
    grok_sentiment: float
    technical_bias: float
    combined_score: float
    reason: str
    current_price: float | None = None
    predicted_move_pct: float | None = None


def _fetch_technical_bias(ticker: str) -> tuple[float, float | None]:
    """Return (directional_bias -1..1, latest_close)."""
    try:
        data = yf.download(ticker, period="3mo", progress=False, auto_adjust=True)
        if data.empty or len(data) < 20:
            return 0.0, None
        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        ret5 = float(close.pct_change(5).iloc[-1])
        ret1 = float(close.pct_change().iloc[-1])
        sma20 = close.rolling(20).mean()
        sma_ratio = float(close.iloc[-1] / sma20.iloc[-1] - 1) if not pd.isna(sma20.iloc[-1]) else 0

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = float(100 - 100 / (1 + rs.iloc[-1])) if not pd.isna(rs.iloc[-1]) else 50

        bias = 0.0
        bias += np.tanh(ret5 * 10) * 0.35
        bias += np.tanh(ret1 * 20) * 0.2
        bias += np.tanh(sma_ratio * 5) * 0.25
        if rsi < 35:
            bias += 0.2
        elif rsi > 65:
            bias -= 0.2

        return float(np.clip(bias, -1, 1)), float(close.iloc[-1])
    except Exception:
        return 0.0, None


class MarketJudge:
    """
    Combines Grok briefing sentiment with technical confirmation.

    Weights: 60% Grok narrative, 40% price momentum (reduces false signals).
    """

    GROK_WEIGHT = 0.6
    TECH_WEIGHT = 0.4
    DIRECTION_THRESHOLD = 0.08

    def __init__(self, briefing: GrokBriefing):
        self.briefing = briefing

    def _signal_for_ticker(self, ticker: str) -> TickerSignal | None:
        if ticker in self.briefing.tickers:
            return self.briefing.tickers[ticker]
        for m in self.briefing.top_movers:
            if m.ticker == ticker:
                return m
        return None

    def predict_ticker(self, ticker: str) -> StockPrediction:
        signal = self._signal_for_ticker(ticker)
        grok_sent = signal.sentiment if signal else self.briefing.overall_mood * 0.5
        grok_reason = signal.reason if signal else f"Using overall mood ({self.briefing.overall_label})"

        tech_bias, price = _fetch_technical_bias(ticker)
        combined = self.GROK_WEIGHT * grok_sent + self.TECH_WEIGHT * tech_bias

        if combined > self.DIRECTION_THRESHOLD:
            direction = "UP"
        elif combined < -self.DIRECTION_THRESHOLD:
            direction = "DOWN"
        else:
            direction = "FLAT"

        confidence = min(abs(combined) * 1.5 + 0.2, 0.95)
        if signal and signal.source == "explicit_score":
            confidence = min(confidence + 0.1, 0.95)

        # Agreement boost when Grok and technicals align
        if grok_sent * tech_bias > 0 and abs(grok_sent) > 0.1 and abs(tech_bias) > 0.1:
            confidence = min(confidence + 0.1, 0.98)

        move_pct = round(combined * 1.5, 2)  # rough next-day estimate

        reason_parts = [f"Grok: {grok_sent:+.2f} ({grok_reason})"]
        reason_parts.append(f"Technical: {tech_bias:+.2f}")
        if grok_sent * tech_bias > 0:
            reason_parts.append("✓ narrative + price agree")
        elif grok_sent * tech_bias < -0.05:
            reason_parts.append("⚠ narrative vs price conflict")

        return StockPrediction(
            ticker=ticker,
            direction=direction,
            confidence=round(confidence, 3),
            grok_sentiment=round(grok_sent, 3),
            technical_bias=round(tech_bias, 3),
            combined_score=round(combined, 3),
            reason=" | ".join(reason_parts),
            current_price=price,
            predicted_move_pct=move_pct,
        )

    def predict_all(self, tickers: list[str]) -> list[StockPrediction]:
        return [self.predict_ticker(t) for t in tickers]

    def top_picks(self, predictions: list[StockPrediction], n: int = 5) -> dict:
        """Highest conviction UP and DOWN picks."""
        ups = sorted(
            [p for p in predictions if p.direction == "UP"],
            key=lambda p: p.confidence * p.combined_score,
            reverse=True,
        )
        downs = sorted(
            [p for p in predictions if p.direction == "DOWN"],
            key=lambda p: p.confidence * abs(p.combined_score),
            reverse=True,
        )
        return {
            "strongest_bullish": ups[:n],
            "strongest_bearish": downs[:n],
        }
