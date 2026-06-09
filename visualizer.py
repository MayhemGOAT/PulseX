"""Chart generation for PulseX reports."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from council.orchestrator import CouncilVerdict


def _ensure_dir(output: str | Path) -> None:
    Path(output).parent.mkdir(parents=True, exist_ok=True)


def plot_council_verdict(verdict: CouncilVerdict, output: str = "images/council_verdict.png") -> None:
    """Bar chart of council member directions and confidence."""
    _ensure_dir(output)
    opinions = verdict.member_opinions
    names = [getattr(op, "member_name", None) or getattr(op, "role", "?") for op in opinions]
    directions = [op.direction for op in opinions]
    confidences = [op.confidence for op in opinions]

    label = getattr(verdict, "label", None)
    if label is None:
        label = "BULLISH" if verdict.direction > 0.05 else "BEARISH" if verdict.direction < -0.05 else "NEUTRAL"
    summary = getattr(verdict, "summary", None) or getattr(verdict, "reasoning", "")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    colors = ["seagreen" if d >= 0 else "indianred" for d in directions]
    ax1.barh(names, directions, color=colors, alpha=0.85)
    ax1.axvline(0, color="gray", linewidth=0.8)
    ax1.set_xlim(-1, 1)
    ax1.set_xlabel("Direction (-1 bearish → +1 bullish)")
    ax1.set_title(f"Council Verdict: {label}")

    ax2.barh(names, confidences, color="steelblue", alpha=0.85)
    ax2.set_xlim(0, 1)
    ax2.set_xlabel("Confidence")
    ax2.set_title(f"Consensus strength: {verdict.consensus_strength:.0%}")

    fig.suptitle(summary, fontsize=10, y=1.02)
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches="tight")
    plt.close()


def plot_backtest_equity(
    equity_curves: dict[str, Any] | pd.Series,
    output: str = "images/backtest_equity.png",
) -> None:
    """Plot one or more equity curves from backtest results."""
    _ensure_dir(output)
    fig, ax = plt.subplots(figsize=(12, 6))

    if isinstance(equity_curves, pd.Series):
        equity_curves = {"strategy": equity_curves}

    for name, equity in equity_curves.items():
        if hasattr(equity, "equity_curve"):
            series = equity.equity_curve
            label = getattr(equity, "name", name)
        elif isinstance(equity, dict) and "equity_curve" in equity:
            series = equity["equity_curve"]
            label = equity.get("name", name)
        else:
            series = equity
            label = name
        ax.plot(series.index, series.values, label=label, linewidth=1.5)

    ax.set_ylabel("Portfolio value ($)")
    ax.set_xlabel("Date")
    ax.set_title("Backtest Equity Curves")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


def plot_sentiment_overlay(
    prices: pd.DataFrame,
    ticker: str,
    output: str = "images/sentiment_overlay.png",
) -> None:
    """Price chart with daily leader sentiment bars."""
    _ensure_dir(output)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax1.plot(prices.index, prices["Close"], label="Price", color="steelblue")
    ax1.set_ylabel("Price ($)")
    ax1.set_title(f"{ticker} — Price vs Leader Sentiment")
    ax1.legend()

    if "leader_sentiment" in prices.columns:
        ax2.bar(prices.index, prices["leader_sentiment"], color="coral", alpha=0.7, width=1)
    ax2.axhline(0, color="gray", linewidth=0.5)
    ax2.set_ylabel("Leader Sentiment")
    ax2.set_xlabel("Date")

    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


def plot_feature_importance(
    model: RandomForestRegressor,
    features: list[str],
    output: str = "images/feature_importance.png",
    top_n: int = 20,
) -> None:
    """Horizontal bar chart of top feature importances."""
    _ensure_dir(output)
    importances = model.feature_importances_
    order = np.argsort(importances)[::-1][:top_n]
    top_features = [features[i] for i in order]
    top_values = importances[order]

    fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.3)))
    ax.barh(top_features[::-1], top_values[::-1], color="teal", alpha=0.85)
    ax.set_xlabel("Importance")
    ax.set_title(f"Top {top_n} Feature Importances")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


def plot_event_timeline(
    events: list[Any],
    prices: pd.DataFrame,
    output: str = "images/event_timeline.png",
) -> None:
    """
    Price chart with high-impact event markers.

    events: objects or dicts with date, leader/handle, impact_score, text (optional).
    """
    _ensure_dir(output)
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(prices.index, prices["Close"], color="steelblue", linewidth=1.2, label="Price")

    for event in events:
        if hasattr(event, "date"):
            date = pd.Timestamp(event.date)
            leader = getattr(event, "leader", getattr(event, "handle", ""))
            score = getattr(event, "impact_score", 0)
            text = getattr(event, "text", "")[:40]
        else:
            date = pd.Timestamp(event["date"])
            leader = event.get("leader", event.get("handle", ""))
            score = event.get("impact_score", 0)
            text = str(event.get("text", ""))[:40]

        color = "green" if score >= 0 else "red"
        ax.axvline(date, color=color, alpha=0.35, linewidth=1)
        price_at = float(prices["Close"].asof(date))
        ax.scatter([date], [price_at], color=color, s=40, zorder=5)
        ax.annotate(
            f"{leader}\n{score:+.2f}",
            xy=(date, price_at),
            xytext=(5, 10),
            textcoords="offset points",
            fontsize=7,
            alpha=0.8,
        )

    ax.set_ylabel("Price ($)")
    ax.set_xlabel("Date")
    ax.set_title("Price vs High-Impact Leader Events")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


def plot_ablation_results(
    results: list[Any],
    output: str = "images/ablation_results.png",
) -> None:
    """Grouped bar chart of A/B ablation metrics (MAE and directional accuracy)."""
    _ensure_dir(output)
    names = [r.name if hasattr(r, "name") else r["name"] for r in results]
    maes = [r.mae if hasattr(r, "mae") else r["mae"] for r in results]
    dir_accs = [r.directional_accuracy if hasattr(r, "directional_accuracy") else r["directional_accuracy"] for r in results]

    x = np.arange(len(names))
    width = 0.35

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twinx()

    bars1 = ax1.bar(x - width / 2, maes, width, label="MAE", color="coral", alpha=0.85)
    bars2 = ax2.bar(x + width / 2, dir_accs, width, label="Dir Accuracy", color="steelblue", alpha=0.85)

    ax1.set_ylabel("MAE (lower is better)")
    ax2.set_ylabel("Directional Accuracy")
    ax2.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, label="Coin flip")
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, rotation=15, ha="right")
    ax1.set_title("A/B Feature Ablation Results")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
