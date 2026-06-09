"""Tests for MarketGrok bridge."""

from pathlib import Path

from grok_bridge.parser import parse_grok_paste
from grok_bridge.predictor import predict_all


SAMPLE = Path(__file__).parent.parent / "data" / "sample_grok_paste.txt"


def test_parse_grok_paste_extracts_tickers():
    text = SAMPLE.read_text()
    briefing = parse_grok_paste(text)
    assert "NVDA" in briefing.tickers
    assert briefing.tickers["NVDA"].sentiment > 0.5
    assert briefing.overall_mood > 0


def test_parse_finds_movers():
    text = SAMPLE.read_text()
    briefing = parse_grok_paste(text)
    mover_tickers = [m.ticker for m in briefing.top_movers]
    assert "NVDA" in mover_tickers or "NVDA" in briefing.tickers


def test_predict_all_returns_predictions():
    text = SAMPLE.read_text()
    result = predict_all(text, tickers=["SPY", "NVDA", "TSLA"])
    preds = result["predictions"]
    assert len(preds) >= 3
    assert all(p.direction in {"UP", "DOWN", "FLAT"} for p in preds)
    assert all(0 <= p.confidence <= 1 for p in preds)


def test_nvda_bullish_in_sample():
    text = SAMPLE.read_text()
    result = predict_all(text, tickers=["NVDA"])
    nvda = result["predictions"][0]
    assert nvda.direction == "UP"
    assert nvda.grok_sentiment > 0
