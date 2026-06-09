"""
PulseX — Market prediction from leader X/Twitter sentiment + AI Council.

Pipeline: fetch prices → score tweets → AI Council deliberates → ML model → backtest → report
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

from backtester import BacktestResult, compare_strategies
from config import load_config
from council import Council
from event_detector import detect_events, get_event_days
from features import add_technical_features, get_feature_columns
from impact_scorer import score_tweets_impact
from leaders import get_leaders_for_ticker
from report import generate_html_report
from tweet_fetcher import fetch_recent_tweets, import_tweets_csv, load_cached_tweets
from tweet_sentiment import add_sentiment_to_prices, score_tweets
from visualizer import (
    plot_ablation_results,
    plot_backtest_equity,
    plot_council_verdict,
    plot_event_timeline,
    plot_feature_importance,
    plot_sentiment_overlay,
)

load_dotenv()
CONFIG = load_config()

TICKER = os.getenv("PULSEX_TICKER", CONFIG["ticker"])
START_DATE = os.getenv("PULSEX_START", CONFIG["start_date"])


@dataclass
class EvalResult:
    name: str
    mae: float
    directional_accuracy: float
    n_samples: int


def fetch_price_data(ticker: str, start: str) -> pd.DataFrame:
    data = yf.download(ticker, start=start, progress=False, auto_adjust=True)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data.index = pd.to_datetime(data.index).tz_localize(None)
    return data.dropna()


def load_tweets(ticker: str) -> pd.DataFrame:
    leaders = get_leaders_for_ticker(ticker)
    try:
        tweets = fetch_recent_tweets(leaders)
    except RuntimeError:
        tweets = load_cached_tweets()
        if tweets.empty:
            sample = CONFIG["data"].get("sample_tweets", "data/sample_tweets.csv")
            if os.path.exists(sample):
                tweets = import_tweets_csv(sample)
    return tweets


def prepare_dataset(ticker: str = TICKER) -> tuple[pd.DataFrame, pd.DataFrame]:
    prices = fetch_price_data(ticker, START_DATE)
    prices = add_technical_features(prices)
    tweets = load_tweets(ticker)

    if not tweets.empty:
        scored = score_tweets(tweets)
        tweets = score_tweets_impact(scored)
        if os.getenv("PULSEX_LLM") == "1":
            from llm_scorer import score_tweets_llm
            tweets = score_tweets_llm(tweets)

    prices = add_sentiment_to_prices(prices, tweets)
    prices["target_return"] = prices["Close"].pct_change().shift(-1)
    prices["target_direction"] = (prices["target_return"] > 0).astype(int)
    prices = prices.dropna()
    return prices, tweets


def build_model() -> RandomForestRegressor:
    m = CONFIG["model"]
    return RandomForestRegressor(
        n_estimators=m.get("n_estimators", 200),
        max_depth=m.get("max_depth", 10),
        min_samples_leaf=m.get("min_samples_leaf", 10),
        min_samples_split=m.get("min_samples_split", 20),
        max_features="sqrt",
        random_state=42,
        n_jobs=-1,
    )


def chronological_split(
    df: pd.DataFrame,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    return df.iloc[:train_end], df.iloc[train_end:val_end], df.iloc[val_end:]


def evaluate_split(
    name: str,
    model: RandomForestRegressor,
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
) -> EvalResult:
    X_train, y_train = train[features], train["target_return"]
    X_test, y_test = test[features], test["target_return"]
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    direction_correct = ((preds > 0) == (y_test > 0)).mean()
    return EvalResult(name=name, mae=mae, directional_accuracy=direction_correct, n_samples=len(test))


def run_ablation(prices: pd.DataFrame) -> list[EvalResult]:
    train, _, test = chronological_split(prices)
    configs = [
        ("technical_only", "technical"),
        ("leader_sentiment_only", "sentiment"),
        ("combined", "combined"),
        ("ai_council_features", "council"),
    ]
    results = []
    for name, mode in configs:
        features = _features_for_mode(prices, mode)
        if not features:
            continue
        model = build_model()
        results.append(evaluate_split(name, model, train, test, features))
    return results


def _features_for_mode(prices: pd.DataFrame, mode: str) -> list[str]:
    if mode == "technical":
        return get_feature_columns(prices, include_sentiment=False)
    if mode == "sentiment":
        return [
            c for c in get_feature_columns(prices, include_sentiment=True)
            if c.startswith("leader_") or c in {"tweet_count", "bullish_tweets", "bearish_tweets", "avg_engagement"}
        ]
    if mode == "council":
        base = get_feature_columns(prices, include_sentiment=True)
        return [c for c in base if c.startswith("leader_") or c in {"rsi_14", "macd", "sma_20_ratio", "high_low_range"}]
    return get_feature_columns(prices, include_sentiment=True)


def walk_forward_eval(
    prices: pd.DataFrame,
    window: int | None = None,
    step: int | None = None,
    include_sentiment: bool = True,
) -> list[EvalResult]:
    bt = CONFIG["backtest"]
    window = window or bt.get("walk_forward_window", 252)
    step = step or bt.get("walk_forward_step", 21)
    features = get_feature_columns(prices, include_sentiment=include_sentiment)
    folds: list[EvalResult] = []

    for start in range(0, len(prices) - window - step, step):
        train = prices.iloc[start : start + window]
        test = prices.iloc[start + window : start + window + step]
        if len(test) < step // 2:
            continue
        model = build_model()
        folds.append(evaluate_split(f"fold_{start}", model, train, test, features))

    if not folds:
        return folds

    avg = EvalResult(
        name="walk_forward_avg",
        mae=float(np.mean([f.mae for f in folds])),
        directional_accuracy=float(np.mean([f.directional_accuracy for f in folds])),
        n_samples=sum(f.n_samples for f in folds),
    )
    return folds + [avg]


def run_council(prices: pd.DataFrame, tweets: pd.DataFrame, ticker: str) -> dict:
    weights = CONFIG.get("council", {}).get("member_weights") or None
    council = Council(weights=weights)
    return council.predict_market(prices, tweets, ticker)


def predict_next_day(prices: pd.DataFrame, include_sentiment: bool = True) -> dict:
    features = get_feature_columns(prices, include_sentiment=include_sentiment)
    model = build_model()
    X, y = prices[features], prices["target_return"]
    model.fit(X, y)

    latest = prices.iloc[-1]
    pred_return = model.predict(latest[features].values.reshape(1, -1))[0]
    current_price = latest["Close"]

    return {
        "ticker": TICKER,
        "date": str(prices.index[-1].date()),
        "current_price": round(current_price, 2),
        "predicted_return_pct": round(pred_return * 100, 2),
        "predicted_price": round(current_price * (1 + pred_return), 2),
        "direction": "UP" if pred_return > 0 else "DOWN",
        "leader_sentiment": round(float(latest.get("leader_sentiment", 0)), 3),
        "tweet_count_today": int(latest.get("tweet_count", 0)),
        "model": model,
        "features": features,
    }


def run_full_backtest(prices: pd.DataFrame, tweets: pd.DataFrame) -> dict[str, BacktestResult]:
    """Backtest on held-out test split only — no in-sample lookahead."""
    train, _, test = chronological_split(prices)
    features = get_feature_columns(prices, include_sentiment=True)

    model = build_model()
    model.fit(train[features], train["target_return"])
    model_preds = pd.Series(model.predict(test[features]), index=test.index)

    council_preds = _build_council_signal_series(test, tweets)
    bt_cfg = CONFIG["backtest"]
    return compare_strategies(
        test,
        model_preds,
        council_preds,
        threshold=bt_cfg.get("threshold", 0.0),
        initial_capital=bt_cfg.get("initial_capital", 100_000),
        scored_tweets=tweets if not tweets.empty else None,
    )


def _build_council_signal_series(prices: pd.DataFrame, tweets: pd.DataFrame) -> pd.Series:
    """Build council direction signal for each bar (for backtesting)."""
    weights = CONFIG.get("council", {}).get("member_weights") or None
    council = Council(weights=weights)
    signals = []
    for i in range(len(prices)):
        row_date = prices.index[i].normalize()
        if not tweets.empty:
            t = tweets.copy()
            t["date"] = pd.to_datetime(t["created_at"], utc=True).dt.tz_convert(None).dt.normalize()
            tweets_today = t[t["date"] == row_date]
        else:
            tweets_today = pd.DataFrame()

        from council.base import CouncilContext

        ctx = CouncilContext(
            price_row=prices.iloc[i],
            tweets=tweets_today,
            ticker=TICKER,
            date=prices.index[i],
        )
        verdict = council.deliberate(ctx)
        signals.append(verdict.direction * verdict.confidence)

    return pd.Series(signals, index=prices.index)


def print_report(
    results: list[EvalResult],
    prediction: dict,
    council_result: dict,
    tweet_count: int,
    backtest: dict | None = None,
) -> None:
    print("=" * 65)
    print("PulseX — AI Council Market Predictor")
    print("=" * 65)
    print(f"Ticker: {TICKER}  |  Tweets loaded: {tweet_count}")
    print()

    print("A/B Feature Comparison (chronological test split):")
    print(f"{'Model':<28} {'MAE':>10} {'Dir Acc':>10} {'N':>8}")
    print("-" * 58)
    for r in results:
        flag = " ✓" if r.directional_accuracy >= 0.5 else " ✗"
        print(f"{r.name:<28} {r.mae:>10.4f} {r.directional_accuracy:>9.1%}{flag} {r.n_samples:>8}")

    print()
    print("AI Council Verdict:")
    print(f"  Label:      {council_result.get('council_label')}")
    print(f"  Direction:  {council_result.get('council_direction', 0):+.4f}")
    print(f"  Confidence: {council_result.get('council_confidence', 0):.1%}")
    print(f"  Consensus:  {council_result.get('consensus_strength', 0):.1%}")
    print()
    for m in council_result.get("members", []):
        print(f"  [{m['name']}] {m['direction']:+.3f} — {m['reasoning']}")

    print()
    print("ML Model Next-Day Prediction:")
    for key in ("current_price", "predicted_price", "predicted_return_pct", "direction", "leader_sentiment"):
        print(f"  {key}: {prediction.get(key)}")

    if backtest:
        print()
        print("Backtest Comparison:")
        print(f"{'Strategy':<22} {'Return':>10} {'Sharpe':>8} {'MaxDD':>10} {'WinRate':>10}")
        print("-" * 62)
        for name, bt in backtest.items():
            print(f"{name:<22} {bt.total_return:>9.2%} {bt.sharpe:>8.2f} {bt.max_drawdown:>9.2%} {bt.win_rate:>9.1%}")

    print("=" * 65)


def main() -> dict:
    """Run full PulseX pipeline and return all results."""
    prices, tweets = prepare_dataset(TICKER)
    results = run_ablation(prices)
    prediction = predict_next_day(prices)
    council_result = run_council(prices, tweets, TICKER)
    backtest = run_full_backtest(prices, tweets)
    events = detect_events(tweets) if not tweets.empty else []

    out_dir = CONFIG["output"]["images_dir"]
    plot_sentiment_overlay(prices, TICKER, f"{out_dir}/sentiment_overlay.png")
    plot_ablation_results(results, f"{out_dir}/ablation_results.png")
    plot_council_verdict(council_result["verdict"], f"{out_dir}/council_verdict.png")
    plot_backtest_equity(backtest, f"{out_dir}/backtest_equity.png")
    if events:
        plot_event_timeline(events, prices, f"{out_dir}/event_timeline.png")
    if "model" in prediction and "features" in prediction:
        plot_feature_importance(prediction["model"], prediction["features"], f"{out_dir}/feature_importance.png")

    report_path = generate_html_report(prediction, council_result, results, backtest, CONFIG["output"]["report_dir"])
    print_report(results, prediction, council_result, len(tweets), backtest)
    print(f"\nReport saved: {report_path}")

    return {
        "prices": prices,
        "tweets": tweets,
        "ablation": results,
        "prediction": prediction,
        "council": council_result,
        "backtest": backtest,
        "events": events,
        "report": report_path,
    }


if __name__ == "__main__":
    main()
