"""Live market movers + Grok buzz cross-reference."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from grok_bridge.parser import GrokBriefing


def fetch_price_movers(tickers: list[str], period: str = "5d") -> pd.DataFrame:
    """Get recent price performance for tickers."""
    rows = []
    for ticker in tickers:
        try:
            data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
            if data.empty:
                continue
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            close = data["Close"]
            rows.append({
                "ticker": ticker,
                "price": round(float(close.iloc[-1]), 2),
                "change_1d_pct": round(float(close.pct_change().iloc[-1]) * 100, 2),
                "change_5d_pct": round(float(close.pct_change(5).iloc[-1]) * 100, 2),
            })
        except Exception:
            continue
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("change_1d_pct", ascending=False)


def cross_reference(briefing: GrokBriefing, price_df: pd.DataFrame) -> pd.DataFrame:
    """Merge Grok buzz with actual price movers."""
    if price_df.empty:
        return price_df

    grok_scores = {t: s.sentiment for t, s in briefing.tickers.items()}
    for m in briefing.top_movers:
        if m.ticker not in grok_scores:
            grok_scores[m.ticker] = m.sentiment

    out = price_df.copy()
    out["grok_sentiment"] = out["ticker"].map(grok_scores).fillna(0)
    out["buzz_price_agree"] = (
        (out["grok_sentiment"] > 0.1) & (out["change_1d_pct"] > 0)
        | (out["grok_sentiment"] < -0.1) & (out["change_1d_pct"] < 0)
    )
    return out.sort_values("change_1d_pct", ascending=False)
