#!/usr/bin/env python3
"""PulseX command-line interface."""

from __future__ import annotations

import argparse
import os
import sys


def _apply_config(config_path: str | None) -> None:
    if config_path:
        os.environ["PULSEX_CONFIG"] = config_path


def _reload_config():
    import importlib
    import config as config_mod
    import pulse_x as pulse_mod

    importlib.reload(config_mod)
    importlib.reload(pulse_mod)
    return pulse_mod


def cmd_run(args: argparse.Namespace) -> int:
    _apply_config(args.config)
    pulse_x = _reload_config()
    if args.ticker:
        os.environ["PULSEX_TICKER"] = args.ticker
    if args.fetch:
        from leaders import get_leaders_for_ticker
        from tweet_fetcher import fetch_recent_tweets

        ticker = args.ticker or pulse_x.TICKER
        try:
            fetch_recent_tweets(get_leaders_for_ticker(ticker))
            print("Fetched live tweets.")
        except RuntimeError as exc:
            print(f"Fetch skipped: {exc}")
    pulse_x.main()
    return 0


def cmd_council(args: argparse.Namespace) -> int:
    _apply_config(args.config)
    pulse_x = _reload_config()
    if args.ticker:
        os.environ["PULSEX_TICKER"] = args.ticker

    from visualizer import plot_council_verdict

    prices, tweets = pulse_x.prepare_dataset(pulse_x.TICKER)
    result = pulse_x.run_council(prices, tweets, pulse_x.TICKER)

    print("=" * 60)
    print("PulseX AI Council Verdict")
    print("=" * 60)
    print(result.get("summary") or result.get("reasoning", ""))
    print()
    for m in result.get("members", []):
        print(f"  [{m['name']}] direction={m['direction']:+.2f}  confidence={m['confidence']:.0%}")
        print(f"    {m['reasoning']}")
    print("=" * 60)

    if args.chart:
        out_dir = pulse_x.CONFIG["output"]["images_dir"]
        os.makedirs(out_dir, exist_ok=True)
        plot_council_verdict(result["verdict"], f"{out_dir}/council_verdict.png")
        print(f"\nChart saved: {out_dir}/council_verdict.png")
    return 0


def cmd_backtest(args: argparse.Namespace) -> int:
    _apply_config(args.config)
    pulse_x = _reload_config()
    if args.ticker:
        os.environ["PULSEX_TICKER"] = args.ticker

    from visualizer import plot_ablation_results, plot_backtest_equity

    prices, tweets = pulse_x.prepare_dataset(pulse_x.TICKER)
    results = pulse_x.run_full_backtest(prices, tweets)
    ablation = pulse_x.run_ablation(prices)

    print(f"\n{'Strategy':<15} {'Return':>10} {'Sharpe':>8} {'MaxDD':>10} {'WinRate':>10} {'Trades':>8}")
    print("-" * 65)
    for name, bt in results.items():
        print(
            f"{bt.name:<15} {bt.total_return:>9.2%} {bt.sharpe:>8.2f} "
            f"{bt.max_drawdown:>9.2%} {bt.win_rate:>9.1%} {bt.trades:>8}"
        )

    out_dir = pulse_x.CONFIG["output"]["images_dir"]
    os.makedirs(out_dir, exist_ok=True)
    plot_backtest_equity(results, f"{out_dir}/backtest_equity.png")
    plot_ablation_results(ablation, f"{out_dir}/ablation_results.png")
    print(f"\nCharts saved: {out_dir}/backtest_equity.png, {out_dir}/ablation_results.png")
    return 0


def cmd_import_tweets(args: argparse.Namespace) -> int:
    from tweet_fetcher import import_tweets_csv

    df = import_tweets_csv(args.csv)
    print(f"Imported {len(df)} tweets into data/tweets_cache.jsonl")
    return 0


def cmd_events(args: argparse.Namespace) -> int:
    _apply_config(args.config)
    pulse_x = _reload_config()
    if args.ticker:
        os.environ["PULSEX_TICKER"] = args.ticker

    from event_detector import detect_events
    from visualizer import plot_event_timeline

    prices, tweets = pulse_x.prepare_dataset(pulse_x.TICKER)
    events = detect_events(tweets)
    print(f"Detected {len(events)} market events:\n")
    for e in events[:20]:
        print(f"  [{e.date}] {e.leader} ({e.event_type}) {e.impact_score:+.3f}")
        print(f"    {e.text[:100]}")
    if events:
        out_dir = pulse_x.CONFIG["output"]["images_dir"]
        os.makedirs(out_dir, exist_ok=True)
        plot_event_timeline(events, prices, f"{out_dir}/event_timeline.png")
        print(f"\nChart saved: {out_dir}/event_timeline.png")
    return 0


def cmd_walkforward(args: argparse.Namespace) -> int:
    _apply_config(args.config)
    pulse_x = _reload_config()
    if args.ticker:
        os.environ["PULSEX_TICKER"] = args.ticker

    prices, _ = pulse_x.prepare_dataset(pulse_x.TICKER)
    results = pulse_x.walk_forward_eval(prices)
    for r in results:
        if r.name == "walk_forward_avg":
            print("\n=== Walk-Forward Average ===")
        print(f"{r.name:<20} MAE={r.mae:.4f}  DirAcc={r.directional_accuracy:.1%}  N={r.n_samples}")
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    _apply_config(args.config)
    if args.ticker:
        tickers = [args.ticker]
    else:
        tickers = args.tickers

    from batch_runner import run_batch

    summary = run_batch(tickers)
    print(f"\n{'Ticker':<8} {'Tweets':>6} {'Dir':>5} {'Ret%':>8} {'Council':>8} {'Status':<20}")
    print("-" * 60)
    for _, row in summary.iterrows():
        ret = f"{row['predicted_return_pct']:+.2f}" if row["predicted_return_pct"] is not None else "—"
        council = f"{row['council_direction']:+.2f}" if row["council_direction"] is not None else "—"
        direction = row["direction"] or "—"
        print(
            f"{row['ticker']:<8} {row['tweet_count']:>6} {direction:>5} {ret:>8} "
            f"{council:>8} {row['status']:<20}"
        )
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    _apply_config(args.config)
    from config import load_config
    from leaders import LEADER_BY_HANDLE, get_leaders_for_ticker
    from tweet_fetcher import fetch_recent_tweets

    cfg = load_config(os.environ.get("PULSEX_CONFIG"))
    ticker = args.ticker or cfg["ticker"]
    handles = cfg.get("leaders", {}).get("handles", [])
    if handles:
        leaders = [LEADER_BY_HANDLE[h.lower()] for h in handles if h.lower() in LEADER_BY_HANDLE]
        leaders = [leader for leader in leaders if ticker.upper() in leader.tickers]
    else:
        leaders = get_leaders_for_ticker(ticker)

    tweets = fetch_recent_tweets(leaders, max_per_user=args.max)
    print(f"Fetched {len(tweets)} tweets from {len(leaders)} leaders")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pulsex",
        description="PulseX — AI Council market predictor using leader X sentiment",
    )
    parser.add_argument("--config", "-c", default=None, help="Path to config.yaml")
    parser.add_argument("--ticker", "-t", help="Target ticker (overrides config/env)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Full pipeline: fetch, council, predict, charts")
    p_run.add_argument("--fetch", action="store_true", help="Attempt live tweet fetch first")
    p_run.set_defaults(func=cmd_run)

    p_council = sub.add_parser("council", help="Run AI council deliberation only")
    p_council.add_argument("--chart", action="store_true", help="Save council verdict chart")
    p_council.set_defaults(func=cmd_council)

    sub.add_parser("backtest", help="Run strategy backtest comparison").set_defaults(func=cmd_backtest)

    p_import = sub.add_parser("import-tweets", help="Import tweets from CSV into cache")
    p_import.add_argument("csv", help="Path to CSV (handle, text, created_at)")
    p_import.set_defaults(func=cmd_import_tweets)

    p_fetch = sub.add_parser("fetch", help="Fetch live tweets from X API")
    p_fetch.add_argument("--max", type=int, default=50, help="Max tweets per leader")
    p_fetch.set_defaults(func=cmd_fetch)

    sub.add_parser("events", help="Detect tier-1 market events").set_defaults(func=cmd_events)
    sub.add_parser("walkforward", help="Run walk-forward validation").set_defaults(func=cmd_walkforward)

    p_batch = sub.add_parser("batch", help="Run pipeline across multiple tickers")
    p_batch.add_argument(
        "tickers",
        nargs="*",
        default=["SPY", "QQQ", "TSLA"],
        help="Tickers to run (default: SPY QQQ TSLA)",
    )
    p_batch.set_defaults(func=cmd_batch)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
