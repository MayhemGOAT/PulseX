"""Tests for batch runner."""

import os

os.environ["PULSEX_FAST"] = "1"

from batch_runner import run_batch


def test_run_batch_returns_summary():
    summary = run_batch(["SPY"])
    assert len(summary) == 1
    assert summary.iloc[0]["ticker"] == "SPY"
    assert summary.iloc[0]["status"] == "ok"
    assert summary.iloc[0]["direction"] in {"UP", "DOWN"}
