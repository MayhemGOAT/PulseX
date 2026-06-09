"""Tests for portfolio module."""

import json
from pathlib import Path

from grok_bridge.judge import StockPrediction
from grok_bridge.portfolio import Portfolio, Holding, add_holding, load_portfolio, recommend_trades, save_portfolio


def test_add_and_load_portfolio(tmp_path):
    path = tmp_path / "portfolio.json"
    pf = Portfolio(holdings=[Holding("AAPL", 10, 180.0)], cash=1000)
    save_portfolio(pf, path)
    loaded = load_portfolio(path)
    assert loaded.tickers == ["AAPL"]
    assert loaded.cash == 1000


def test_recommend_trim_on_bearish():
    pf = Portfolio(holdings=[Holding("TSLA", 10, 200.0)])
    preds = {
        "TSLA": StockPrediction(
            ticker="TSLA",
            direction="DOWN",
            confidence=0.75,
            grok_sentiment=-0.5,
            technical_bias=-0.3,
            combined_score=-0.42,
            reason="bearish",
            current_price=180.0,
        ),
    }
    actions = recommend_trades(pf, preds)
    assert actions[0].action in {"TRIM", "SELL"}
    assert actions[0].ticker == "TSLA"


def test_watch_new_buzzing_ticker():
    pf = Portfolio(holdings=[Holding("AAPL", 5, 180.0)])
    preds = {
        "AAPL": StockPrediction("AAPL", "UP", 0.6, 0.3, 0.2, 0.26, "ok", 190.0),
        "SMCI": StockPrediction("SMCI", "UP", 0.8, 0.9, 0.3, 0.66, "buzz", 45.0),
    }
    actions = recommend_trades(pf, preds, buzzing_tickers=["SMCI"])
    watch = [a for a in actions if a.action == "WATCH"]
    assert any(a.ticker == "SMCI" for a in watch)
