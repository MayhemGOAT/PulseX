"""Integration smoke test for PulseX pipeline."""

import os

import pytest

os.environ["PULSEX_FAST"] = "1"

from pulse_x import prepare_dataset, run_ablation, run_council, TICKER


def test_prepare_dataset():
    prices, tweets = prepare_dataset(TICKER)
    if prices.empty:
        pytest.skip("yfinance unavailable — network required for integration test")
    assert len(prices) > 100
    assert "leader_sentiment" in prices.columns
    assert "target_return" in prices.columns


def test_ablation_runs():
    prices, _ = prepare_dataset(TICKER)
    if prices.empty:
        pytest.skip("yfinance unavailable — network required for integration test")
    results = run_ablation(prices)
    assert len(results) >= 3
    assert all(0 <= r.directional_accuracy <= 1 for r in results)


def test_council_runs():
    prices, tweets = prepare_dataset(TICKER)
    if prices.empty:
        pytest.skip("yfinance unavailable — network required for integration test")
    result = run_council(prices, tweets, TICKER)
    assert "council_direction" in result
    assert len(result["members"]) == 5
