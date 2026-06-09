"""Load PulseX configuration from config.yaml with defaults fallback."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from leaders import MARKET_LEADERS

CONFIG_PATH = Path(__file__).parent / "config.yaml"

DEFAULTS = {
    "ticker": "SPY",
    "start_date": "2018-01-01",
    "model": {
        "n_estimators": 200,
        "max_depth": 10,
        "min_samples_leaf": 10,
        "min_samples_split": 20,
    },
    "council": {
        "member_weights": {},
    },
    "leaders": {
        "handles": [leader.handle for leader in MARKET_LEADERS],
    },
    "backtest": {
        "train_ratio": 0.7,
        "val_ratio": 0.15,
        "walk_forward_window": 252,
        "walk_forward_step": 21,
        "initial_capital": 100_000,
        "threshold": 0.0,
        "commission": 0.001,
        "council_threshold": 0.1,
        "event_min_weight": 0.85,
    },
    "data": {
        "tweet_cache": "data/tweets_cache.jsonl",
        "sample_tweets": "data/sample_tweets.csv",
    },
    "output": {
        "images_dir": "images",
        "report_dir": "reports",
    },
}


def load_config(path: Path | str | None = None) -> dict:
    """Load config from YAML; missing keys fall back to defaults."""
    if path is None:
        env_path = os.environ.get("PULSEX_CONFIG")
        path = Path(env_path) if env_path else CONFIG_PATH
    else:
        path = Path(path)
    config = _copy_defaults(DEFAULTS)
    if path.exists():
        with open(path) as f:
            user = yaml.safe_load(f) or {}
        _deep_merge(config, user)
    return config


def _copy_defaults(defaults: dict) -> dict:
    return {key: (val.copy() if isinstance(val, dict) else val) for key, val in defaults.items()}


def _deep_merge(base: dict, override: dict) -> None:
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
