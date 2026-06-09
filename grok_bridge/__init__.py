"""MarketGrok Bridge — free Grok copy-paste → local judge → multi-stock predictions."""

from grok_bridge.judge import MarketJudge
from grok_bridge.parser import parse_grok_paste
from grok_bridge.predictor import predict_all

__all__ = ["MarketJudge", "parse_grok_paste", "predict_all"]
