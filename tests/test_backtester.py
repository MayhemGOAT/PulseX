"""Tests for backtester."""

import numpy as np
import pandas as pd

from backtester import run_backtest


def _make_prices(n: int = 100) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    prices = 100 * (1 + np.random.randn(n) * 0.01).cumprod()
    return pd.DataFrame({"Close": prices}, index=dates)


def test_run_backtest_returns_metrics():
    prices = _make_prices()
    preds = pd.Series(0.001, index=prices.index)
    result = run_backtest(prices, preds)
    assert result.trades >= 0
    assert -1 <= result.total_return <= 10
    assert len(result.equity_curve) >= len(prices) - 2


def test_positive_predictions_go_long():
    prices = _make_prices(50)
    preds = pd.Series(0.01, index=prices.index)
    result = run_backtest(prices, preds, threshold=0.0)
    assert result.trades >= 1
