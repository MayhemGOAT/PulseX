"""Technical indicator features (subset from FinPulse — scale-invariant)."""

import numpy as np
import pandas as pd


def add_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer technical indicators from OHLCV. Raw prices excluded from model input."""
    out = df.copy()
    close = out["Close"]
    volume = out["Volume"]

    for window in (5, 10, 20, 50):
        sma = close.rolling(window).mean()
        out[f"sma_{window}_ratio"] = close / sma - 1

    out["rsi_14"] = _rsi(close, 14)
    out["macd"], out["macd_signal"] = _macd(close)
    out["bb_position"] = _bollinger_position(close, 20)

    out["return_1d"] = close.pct_change()
    for lag in (1, 2, 3, 5):
        out[f"return_lag_{lag}"] = out["return_1d"].shift(lag)

    out["volume_ratio_20"] = volume / volume.rolling(20).mean() - 1
    out["high_low_range"] = (out["High"] - out["Low"]) / close
    out["close_open_ratio"] = out["Close"] / out["Open"] - 1

    return out


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd / series, signal / series


def _bollinger_position(series: pd.Series, window: int) -> pd.Series:
    sma = series.rolling(window).mean()
    std = series.rolling(window).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    return (series - lower) / (upper - lower).replace(0, np.nan)


def get_feature_columns(df: pd.DataFrame, include_sentiment: bool = True) -> list[str]:
    """Return model feature column names."""
    exclude = {"Open", "High", "Low", "Close", "Volume", "Adj Close", "target_return", "target_direction"}
    cols = [c for c in df.columns if c not in exclude and df[c].dtype in ("float64", "int64", "float32")]
    if not include_sentiment:
        cols = [c for c in cols if not c.startswith("leader_") and c not in {
            "tweet_count", "bullish_tweets", "bearish_tweets", "avg_engagement"
        }]
    return cols
