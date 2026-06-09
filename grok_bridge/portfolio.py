"""Portfolio management and trade recommendations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yfinance as yf

from grok_bridge.judge import StockPrediction

PORTFOLIO_PATH = Path(__file__).parent.parent / "data" / "portfolio.json"


@dataclass
class Holding:
    ticker: str
    shares: float
    avg_cost: float | None = None

    @property
    def cost_basis(self) -> float | None:
        if self.avg_cost is None:
            return None
        return self.shares * self.avg_cost


@dataclass
class Portfolio:
    holdings: list[Holding] = field(default_factory=list)
    cash: float = 0.0
    notes: str = ""

    @property
    def tickers(self) -> list[str]:
        return [h.ticker.upper() for h in self.holdings]


def load_portfolio(path: Path | None = None) -> Portfolio:
    path = path or PORTFOLIO_PATH
    if not path.exists():
        return Portfolio()
    data = json.loads(path.read_text())
    holdings = [
        Holding(
            ticker=h["ticker"].upper(),
            shares=float(h["shares"]),
            avg_cost=float(h["avg_cost"]) if h.get("avg_cost") is not None else None,
        )
        for h in data.get("holdings", [])
    ]
    return Portfolio(
        holdings=holdings,
        cash=float(data.get("cash", 0)),
        notes=data.get("notes", ""),
    )


def save_portfolio(portfolio: Portfolio, path: Path | None = None) -> None:
    path = path or PORTFOLIO_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "holdings": [
            {
                "ticker": h.ticker,
                "shares": h.shares,
                "avg_cost": h.avg_cost,
            }
            for h in portfolio.holdings
        ],
        "cash": portfolio.cash,
        "notes": portfolio.notes,
    }
    path.write_text(json.dumps(data, indent=2))


def add_holding(ticker: str, shares: float, avg_cost: float | None = None) -> Portfolio:
    portfolio = load_portfolio()
    ticker = ticker.upper()
    for h in portfolio.holdings:
        if h.ticker == ticker:
            h.shares += shares
            if avg_cost is not None:
                h.avg_cost = avg_cost
            save_portfolio(portfolio)
            return portfolio
    portfolio.holdings.append(Holding(ticker=ticker, shares=shares, avg_cost=avg_cost))
    save_portfolio(portfolio)
    return portfolio


def remove_holding(ticker: str) -> Portfolio:
    portfolio = load_portfolio()
    portfolio.holdings = [h for h in portfolio.holdings if h.ticker != ticker.upper()]
    save_portfolio(portfolio)
    return portfolio


@dataclass
class TradeAction:
    ticker: str
    action: str       # HOLD, ADD, TRIM, SELL, WATCH (new idea)
    confidence: float
    direction: str
    reason: str
    shares: float | None = None
    unrealized_pnl_pct: float | None = None
    current_price: float | None = None
    position_value: float | None = None


def _unrealized_pnl(holding: Holding, price: float | None) -> float | None:
    if holding.avg_cost is None or price is None or holding.avg_cost == 0:
        return None
    return (price / holding.avg_cost - 1) * 100


def recommend_trades(
    portfolio: Portfolio,
    predictions: dict[str, StockPrediction],
    buzzing_tickers: list[str] | None = None,
) -> list[TradeAction]:
    """Generate HOLD/ADD/TRIM/SELL/WATCH actions for portfolio + new ideas."""
    actions: list[TradeAction] = []
    buzzing = set((buzzing_tickers or []))

    for holding in portfolio.holdings:
        pred = predictions.get(holding.ticker)
        if not pred:
            actions.append(TradeAction(
                ticker=holding.ticker,
                action="HOLD",
                confidence=0.3,
                direction="FLAT",
                reason="No Grok signal — hold and gather more data",
                shares=holding.shares,
            ))
            continue

        pnl = _unrealized_pnl(holding, pred.current_price)
        pos_val = (holding.shares * pred.current_price) if pred.current_price else None
        action, reason = _action_for_holding(holding, pred, pnl)

        actions.append(TradeAction(
            ticker=holding.ticker,
            action=action,
            confidence=pred.confidence,
            direction=pred.direction,
            reason=reason,
            shares=holding.shares,
            unrealized_pnl_pct=round(pnl, 2) if pnl is not None else None,
            current_price=pred.current_price,
            position_value=round(pos_val, 2) if pos_val else None,
        ))

    # New ideas: bullish buzz not in portfolio
    held = set(portfolio.tickers)
    for ticker in buzzing:
        if ticker in held:
            continue
        pred = predictions.get(ticker)
        if pred and pred.direction == "UP" and pred.confidence >= 0.5:
            actions.append(TradeAction(
                ticker=ticker,
                action="WATCH",
                confidence=pred.confidence,
                direction=pred.direction,
                reason=f"Not in portfolio — buzzing on X, bullish signal ({pred.reason[:60]})",
                current_price=pred.current_price,
            ))

    priority = {"SELL": 0, "TRIM": 1, "ADD": 2, "WATCH": 3, "HOLD": 4}
    actions.sort(key=lambda a: (priority.get(a.action, 5), -a.confidence))
    return actions


def _action_for_holding(
    holding: Holding,
    pred: StockPrediction,
    pnl: float | None,
) -> tuple[str, str]:
    grok = pred.grok_sentiment
    tech = pred.technical_bias
    agree = grok * tech > 0

    if pred.direction == "DOWN" and pred.confidence >= 0.55:
        if pnl is not None and pnl > 15:
            return "TRIM", f"Grok bearish ({pred.confidence:.0%}) but you're up {pnl:+.1f}% — take profits"
        if pred.confidence >= 0.7:
            return "SELL", f"Strong bearish signal ({pred.confidence:.0%}) — Grok + judge say DOWN"
        return "TRIM", f"Bearish lean ({pred.confidence:.0%}) — reduce exposure"

    if pred.direction == "UP" and pred.confidence >= 0.55 and agree:
        if pnl is not None and pnl < -10:
            return "ADD", f"Bullish ({pred.confidence:.0%}), down {pnl:.1f}% — potential dip buy if thesis intact"
        return "HOLD", f"Bullish ({pred.confidence:.0%}) — narrative + price agree, stay long"

    if pred.direction == "UP" and not agree:
        return "HOLD", "Grok bullish but price weak — wait for confirmation before adding"

    if pred.direction == "FLAT":
        return "HOLD", f"No clear edge ({pred.confidence:.0%}) — sit tight"

    return "HOLD", pred.reason[:100]


def portfolio_summary(portfolio: Portfolio) -> dict:
    """Fetch live values for portfolio holdings."""
    rows = []
    total_value = portfolio.cash
    for h in portfolio.holdings:
        try:
            data = yf.download(h.ticker, period="5d", progress=False, auto_adjust=True)
            if data.empty:
                continue
            close = data["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            price = float(close.iloc[-1])
            value = h.shares * price
            total_value += value
            pnl = _unrealized_pnl(h, price)
            rows.append({
                "ticker": h.ticker,
                "shares": h.shares,
                "price": round(price, 2),
                "value": round(value, 2),
                "pnl_pct": round(pnl, 2) if pnl is not None else None,
            })
        except Exception:
            continue
    return {"holdings": rows, "cash": portfolio.cash, "total_value": round(total_value, 2)}
