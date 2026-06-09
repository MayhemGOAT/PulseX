#!/usr/bin/env python3
"""
MarketGrok — Free Grok copy-paste → local judge → multi-stock predictions.

Workflow:
  1. python3 market_grok.py prompts          # see commands to copy
  2. python3 market_grok.py prompt market_pulse   # copy output → grok.com
  3. Paste Grok's answer into data/my_briefing.txt
  4. python3 market_grok.py analyze data/my_briefing.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from grok_bridge.parser import DEFAULT_TICKERS
from grok_bridge.portfolio import add_holding, load_portfolio, remove_holding, save_portfolio
from grok_bridge.predictor import predict_all
from grok_bridge.prompts import PROMPTS, get_prompt, list_prompts


def cmd_prompts(_: argparse.Namespace) -> int:
    print(list_prompts())
    return 0


def cmd_prompt(args: argparse.Namespace) -> int:
    portfolio = load_portfolio()
    holdings = [
        {"ticker": h.ticker, "shares": h.shares, "avg_cost": h.avg_cost}
        for h in portfolio.holdings
    ]
    try:
        text = get_prompt(args.name, ticker=args.ticker, portfolio_holdings=holdings)
    except KeyError as e:
        print(e)
        return 1
    print("=" * 70)
    print(f"COPY THIS INTO GROK (grok.com or X app):")
    print(f"Prompt: {PROMPTS[args.name]['title']}")
    print("=" * 70)
    print()
    print(text)
    print()
    print("=" * 70)
    print("After Grok responds, save the answer and run:")
    print(f"  python3 market_grok.py analyze <your_file.txt>")
    print("=" * 70)
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}")
        return 1

    text = path.read_text()
    tickers = args.tickers or None
    portfolio = load_portfolio()
    result = predict_all(text, tickers, portfolio=portfolio)

    briefing = result["briefing"]
    predictions = result["predictions"]
    picks = result["picks"]

    print("=" * 70)
    print("MarketGrok — Judge Report")
    print("=" * 70)
    print(f"Overall mood: {briefing.overall_label} ({briefing.overall_mood:+.2f})")
    if briefing.themes:
        print(f"Themes: {', '.join(briefing.themes[:3])}")
    if briefing.risks:
        print(f"Risks: {', '.join(briefing.risks[:2])}")
    print()

    print(f"{'Ticker':<8} {'Dir':<6} {'Conf':>6} {'Grok':>7} {'Tech':>7} {'Price':>10} {'Est%':>7}")
    print("-" * 70)
    for p in sorted(predictions, key=lambda x: abs(x.combined_score), reverse=True):
        price = f"${p.current_price:.2f}" if p.current_price else "—"
        est = f"{p.predicted_move_pct:+.1f}%" if p.predicted_move_pct else "—"
        print(
            f"{p.ticker:<8} {p.direction:<6} {p.confidence:>5.0%} "
            f"{p.grok_sentiment:>+6.2f} {p.technical_bias:>+6.2f} {price:>10} {est:>7}"
        )

    print()
    print("🟢 STRONGEST BULLISH PICKS:")
    for p in picks["strongest_bullish"][:3]:
        print(f"   {p.ticker} {p.direction} ({p.confidence:.0%}) — {p.reason[:80]}")

    print()
    print("🔴 STRONGEST BEARISH PICKS:")
    for p in picks["strongest_bearish"][:3]:
        print(f"   {p.ticker} {p.direction} ({p.confidence:.0%}) — {p.reason[:80]}")

    movers = result["price_movers"]
    if not movers.empty:
        print()
        print("📈 PRICE MOVERS vs GROK BUZZ:")
        print(f"{'Ticker':<8} {'1D%':>8} {'5D%':>8} {'Grok':>7} {'Agree':>6}")
        print("-" * 45)
        for _, row in movers.head(8).iterrows():
            agree = "✓" if row.get("buzz_price_agree") else "✗"
            print(
                f"{row['ticker']:<8} {row['change_1d_pct']:>+7.1f}% "
                f"{row['change_5d_pct']:>+7.1f}% {row['grok_sentiment']:>+6.2f} {agree:>6}"
            )

    _print_portfolio_section(result)

    print()
    print("=" * 70)
    _print_accuracy_disclaimer()
    return 0


def _print_portfolio_section(result: dict) -> None:
    summary = result.get("portfolio_summary")
    actions = result.get("trade_actions", [])
    portfolio = result.get("portfolio")

    if not portfolio or not portfolio.holdings:
        print()
        print("💼 PORTFOLIO: none set — add holdings:")
        print("   python3 market_grok.py portfolio add NVDA 5 120")
        print("   python3 market_grok.py portfolio show")
        return

    print()
    print("=" * 70)
    print("💼 YOUR PORTFOLIO")
    print("=" * 70)
    if summary:
        print(f"Total value: ${summary['total_value']:,.2f}  (cash: ${summary['cash']:,.2f})")
        print(f"{'Ticker':<8} {'Shares':>8} {'Price':>10} {'Value':>12} {'P&L%':>8}")
        print("-" * 50)
        for row in summary["holdings"]:
            pnl = f"{row['pnl_pct']:+.1f}%" if row["pnl_pct"] is not None else "—"
            print(
                f"{row['ticker']:<8} {row['shares']:>8.1f} "
                f"${row['price']:>9.2f} ${row['value']:>10,.2f} {pnl:>8}"
            )

    if actions:
        print()
        print("📋 TRADE RECOMMENDATIONS (judge + Grok):")
        print(f"{'Ticker':<8} {'Action':<6} {'Dir':<6} {'Conf':>6} {'P&L%':>8}  Reason")
        print("-" * 70)
        for a in actions:
            pnl = f"{a.unrealized_pnl_pct:+.1f}%" if a.unrealized_pnl_pct is not None else "—"
            icon = {"SELL": "🔴", "TRIM": "🟠", "ADD": "🟢", "WATCH": "👀", "HOLD": "⚪"}.get(a.action, "")
            print(
                f"{icon} {a.ticker:<6} {a.action:<6} {a.direction:<6} {a.confidence:>5.0%} "
                f"{pnl:>8}  {a.reason[:45]}"
            )


def cmd_interactive(_: argparse.Namespace) -> int:
    print("MarketGrok Interactive Mode")
    print("-" * 40)
    print("Step 1: Copy a prompt")
    print("  python3 market_grok.py prompt market_pulse")
    print()
    print("Step 2: Paste into grok.com, wait for answer")
    print()
    print("Step 3: Paste Grok's full response below (Ctrl+D when done):\n")
    lines = sys.stdin.read()
    if not lines.strip():
        print("No input received.")
        return 1

    out = Path("data/last_grok_paste.txt")
    out.parent.mkdir(exist_ok=True)
    out.write_text(lines)

    result = predict_all(lines)
    predictions = result["predictions"]
    print(f"\n✓ Saved to {out}")
    print(f"\nQuick results ({len(predictions)} stocks):")
    for p in sorted(predictions, key=lambda x: x.confidence, reverse=True)[:5]:
        print(f"  {p.ticker}: {p.direction} ({p.confidence:.0%})")
    return 0


def _print_accuracy_disclaimer() -> None:
    print("NOTE: No model guarantees 60%+ or 100% directional accuracy.")
    print("      Grok narrative + technical confirmation improves signal quality,")
    print("      but markets are noisy. Use for research, not financial advice.")
    print("      Track results: python3 market_grok.py evaluate <past_file.txt>")


def cmd_portfolio(args: argparse.Namespace) -> int:
    if args.subcmd == "show":
        pf = load_portfolio()
        if not pf.holdings:
            print("Portfolio empty. Example:")
            print("  python3 market_grok.py portfolio add AAPL 10 185")
            return 0
        from grok_bridge.portfolio import portfolio_summary
        s = portfolio_summary(pf)
        print(f"Cash: ${pf.cash:,.2f}")
        print(f"Total: ${s['total_value']:,.2f}\n")
        for row in s["holdings"]:
            cost = next((h.avg_cost for h in pf.holdings if h.ticker == row["ticker"]), None)
            cost_s = f"@ ${cost:.2f}" if cost else ""
            pnl = f" ({row['pnl_pct']:+.1f}%)" if row["pnl_pct"] is not None else ""
            print(f"  {row['ticker']}: {row['shares']} shares {cost_s} → ${row['value']:,.2f}{pnl}")
        if pf.notes:
            print(f"\nNotes: {pf.notes}")
        return 0

    if args.subcmd == "add":
        add_holding(args.ticker, args.shares, args.avg_cost)
        print(f"Added {args.shares} shares of {args.ticker.upper()}")
        return 0

    if args.subcmd == "remove":
        remove_holding(args.ticker)
        print(f"Removed {args.ticker.upper()} from portfolio")
        return 0

    if args.subcmd == "set-cash":
        pf = load_portfolio()
        pf.cash = args.amount
        save_portfolio(pf)
        print(f"Cash set to ${args.amount:,.2f}")
        return 0

    return 1


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Check how past predictions would have performed (honest backtest)."""
    import yfinance as yf

    path = Path(args.file)
    text = path.read_text()
    result = predict_all(text)
    predictions = result["predictions"]

    print("Evaluating next-day direction accuracy (honest check):\n")
    correct = 0
    total = 0

    for p in predictions:
        if p.direction == "FLAT" or p.current_price is None:
            continue
        try:
            data = yf.download(p.ticker, period="5d", progress=False, auto_adjust=True)
            if len(data) < 2:
                continue
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            actual_ret = float(data["Close"].pct_change().iloc[-1])
            actual_dir = "UP" if actual_ret > 0 else "DOWN"
            hit = actual_dir == p.direction
            correct += int(hit)
            total += 1
            mark = "✓" if hit else "✗"
            print(f"  {mark} {p.ticker}: predicted {p.direction}, actual {actual_dir} ({actual_ret:+.2%})")
        except Exception:
            continue

    if total:
        acc = correct / total
        print(f"\nDirectional accuracy: {acc:.1%} ({correct}/{total})")
        print("(Based on most recent trading day — not a guarantee of future performance)")
    else:
        print("Could not evaluate — insufficient price data.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="market_grok",
        description="MarketGrok — free Grok paste → multi-stock predictions",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("prompts", help="List copy-paste Grok commands").set_defaults(func=cmd_prompts)

    p_prompt = sub.add_parser("prompt", help="Print a Grok command to copy")
    p_prompt.add_argument("name", choices=list(PROMPTS.keys()))
    p_prompt.add_argument("--ticker", help="For single_stock prompt")
    p_prompt.set_defaults(func=cmd_prompt)

    p_analyze = sub.add_parser("analyze", help="Analyze pasted Grok response")
    p_analyze.add_argument("file", help="Text file with Grok's answer")
    p_analyze.add_argument("--tickers", nargs="*", help="Override ticker list")
    p_analyze.set_defaults(func=cmd_analyze)

    sub.add_parser("interactive", help="Paste Grok response in terminal").set_defaults(func=cmd_interactive)

    p_eval = sub.add_parser("evaluate", help="Check past prediction accuracy")
    p_eval.add_argument("file", help="Past Grok paste file")
    p_eval.set_defaults(func=cmd_evaluate)

    p_pf = sub.add_parser("portfolio", help="Manage your holdings")
    pf_sub = p_pf.add_subparsers(dest="subcmd", required=True)
    pf_sub.add_parser("show", help="Show portfolio").set_defaults(func=cmd_portfolio, subcmd="show")
    p_add = pf_sub.add_parser("add", help="Add/update holding")
    p_add.add_argument("ticker")
    p_add.add_argument("shares", type=float)
    p_add.add_argument("avg_cost", type=float, nargs="?", default=None)
    p_add.set_defaults(func=cmd_portfolio, subcmd="add")
    p_rm = pf_sub.add_parser("remove", help="Remove holding")
    p_rm.add_argument("ticker")
    p_rm.set_defaults(func=cmd_portfolio, subcmd="remove")
    p_cash = pf_sub.add_parser("set-cash", help="Set cash balance")
    p_cash.add_argument("amount", type=float)
    p_cash.set_defaults(func=cmd_portfolio, subcmd="set-cash")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
