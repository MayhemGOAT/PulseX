"""Top-level prediction orchestrator."""

from __future__ import annotations

from grok_bridge.judge import MarketJudge, StockPrediction
from grok_bridge.movers import cross_reference, fetch_price_movers
from grok_bridge.parser import DEFAULT_TICKERS, GrokBriefing, parse_grok_paste
from grok_bridge.portfolio import Portfolio, load_portfolio, recommend_trades


def predict_all(
    grok_text: str,
    tickers: list[str] | None = None,
    portfolio: Portfolio | None = None,
) -> dict:
    """Full pipeline: parse Grok paste → judge → multi-stock predictions."""
    portfolio = portfolio or load_portfolio()
    tickers = list(tickers or DEFAULT_TICKERS)
    for t in portfolio.tickers:
        if t not in tickers:
            tickers.append(t)

    briefing = parse_grok_paste(grok_text, tickers)
    judge = MarketJudge(briefing)
    predictions = judge.predict_all(tickers)

    # Include movers mentioned by Grok not in default list
    extra = [m.ticker for m in briefing.top_movers if m.ticker not in tickers]
    if extra:
        predictions.extend(judge.predict_all(extra[:5]))

    picks = judge.top_picks(predictions)
    all_tickers = list({p.ticker for p in predictions})
    price_movers = fetch_price_movers(all_tickers)
    merged = cross_reference(briefing, price_movers)

    pred_map = {p.ticker: p for p in predictions}
    trade_actions = []
    portfolio_summary = None
    if portfolio.holdings:
        buzzing = [m.ticker for m in briefing.top_movers] + list(briefing.tickers.keys())
        trade_actions = recommend_trades(portfolio, pred_map, buzzing)
        from grok_bridge.portfolio import portfolio_summary as _ps
        portfolio_summary = _ps(portfolio)

    return {
        "briefing": briefing,
        "predictions": predictions,
        "picks": picks,
        "price_movers": merged,
        "overall_mood": briefing.overall_mood,
        "themes": briefing.themes,
        "risks": briefing.risks,
        "portfolio": portfolio,
        "trade_actions": trade_actions,
        "portfolio_summary": portfolio_summary,
    }
