"""Run PulseX pipeline across multiple tickers."""

from __future__ import annotations

import os

import pandas as pd

from pulse_x import predict_next_day, prepare_dataset, run_council


def run_batch(tickers: list[str]) -> pd.DataFrame:
    """Run pipeline per ticker and return a summary DataFrame."""
    rows = []
    for ticker in tickers:
        os.environ["PULSEX_TICKER"] = ticker.upper()
        try:
            prices, tweets = prepare_dataset(ticker)
            prediction = predict_next_day(prices)
            council = run_council(prices, tweets, ticker)
            rows.append({
                "ticker": ticker.upper(),
                "tweet_count": len(tweets),
                "direction": prediction["direction"],
                "predicted_return_pct": prediction["predicted_return_pct"],
                "leader_sentiment": prediction["leader_sentiment"],
                "council_direction": round(float(council.get("council_direction", 0)), 4),
                "council_confidence": round(float(council.get("council_confidence", 0)), 4),
                "status": "ok",
            })
        except Exception as exc:
            rows.append({
                "ticker": ticker.upper(),
                "tweet_count": 0,
                "direction": None,
                "predicted_return_pct": None,
                "leader_sentiment": None,
                "council_direction": None,
                "council_confidence": None,
                "status": f"error: {exc}",
            })
    return pd.DataFrame(rows)
