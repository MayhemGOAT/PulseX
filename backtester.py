"""Chronological backtesting for PulseX prediction strategies."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from event_detector import filter_event_periods, get_event_days


@dataclass
class BacktestResult:
    name: str = "strategy"
    total_return: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    trades: int = 0
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))

    @property
    def n_trades(self) -> int:
        return self.trades


def _align_predictions(prices: pd.DataFrame, predictions: pd.Series | np.ndarray) -> pd.Series:
    if isinstance(predictions, pd.Series):
        return predictions.reindex(prices.index)
    return pd.Series(np.asarray(predictions), index=prices.index)


def _strategy_returns(
    prices: pd.DataFrame,
    predictions: pd.Series,
    threshold: float,
) -> tuple[pd.Series, pd.Series]:
    forward_return = prices["Close"].pct_change().shift(-1)
    signal = (predictions > threshold).astype(float)
    signal.iloc[-1] = 0.0
    strat_returns = signal.shift(1).fillna(0) * forward_return
    return strat_returns.dropna(), signal


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max.replace(0, np.nan)
    return float(drawdown.min())


def _sharpe_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    if len(returns) < 2 or returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * np.sqrt(periods_per_year))


def run_backtest(
    prices: pd.DataFrame,
    predictions: pd.Series | np.ndarray,
    name: str = "strategy",
    threshold: float = 0.0,
    initial_capital: float = 100_000,
) -> BacktestResult:
    """Long/flat backtest on chronological data — no lookahead."""
    preds = _align_predictions(prices, predictions)
    valid = preds.notna() & prices["Close"].notna()
    prices = prices.loc[valid]
    preds = preds.loc[valid]

    strat_returns, signal = _strategy_returns(prices, preds, threshold)
    equity = initial_capital * (1.0 + strat_returns.fillna(0.0)).cumprod()

    trades = int((signal.diff().abs() > 0).sum())
    active = strat_returns[strat_returns != 0]
    win_rate = float((active > 0).mean()) if len(active) else 0.0

    return BacktestResult(
        name=name,
        total_return=float(equity.iloc[-1] / initial_capital - 1.0) if len(equity) else 0.0,
        sharpe=_sharpe_ratio(strat_returns.dropna()),
        max_drawdown=_max_drawdown(equity),
        win_rate=win_rate,
        trades=trades,
        equity_curve=equity,
    )


def compare_strategies(
    prices: pd.DataFrame,
    model_preds: pd.Series | np.ndarray,
    council_preds: pd.Series | np.ndarray,
    event_only: bool = False,
    scored_tweets: pd.DataFrame | None = None,
    threshold: float = 0.0,
    initial_capital: float = 100_000,
) -> dict[str, BacktestResult]:
    """Compare ML model, AI council, and buy-and-hold."""
    test_prices = prices.copy()
    if event_only:
        if scored_tweets is None:
            raise ValueError("scored_tweets required when event_only=True")
        event_days = get_event_days(scored_tweets)
        test_prices = filter_event_periods(prices, event_days)

    results: dict[str, BacktestResult] = {
        "model": run_backtest(
            test_prices, model_preds, name="model", threshold=threshold, initial_capital=initial_capital
        ),
        "council": run_backtest(
            test_prices, council_preds, name="council", threshold=threshold, initial_capital=initial_capital
        ),
    }

    bh_returns = test_prices["Close"].pct_change().fillna(0)
    bh_equity = initial_capital * (1 + bh_returns).cumprod()
    results["buy_hold"] = BacktestResult(
        name="buy_hold",
        total_return=float(bh_equity.iloc[-1] / initial_capital - 1.0) if len(bh_equity) else 0.0,
        sharpe=_sharpe_ratio(bh_returns),
        max_drawdown=_max_drawdown(bh_equity),
        win_rate=float((bh_returns > 0).mean()) if len(bh_returns) else 0.0,
        trades=1,
        equity_curve=bh_equity,
    )

    if event_only and not test_prices.empty:
        results["model_event_only"] = results["model"]
        results["council_event_only"] = results["council"]

    return results
