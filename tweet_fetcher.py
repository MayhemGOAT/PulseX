"""Fetch and cache tweets from market-moving leaders via X API v2."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from leaders import MARKET_LEADERS, Leader

DATA_DIR = Path(__file__).parent / "data"
TWEET_CACHE = DATA_DIR / "tweets_cache.jsonl"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _get_twitter_client():
    """Return tweepy Client if credentials are configured."""
    bearer = os.getenv("X_BEARER_TOKEN")
    if not bearer:
        return None
    import tweepy

    return tweepy.Client(bearer_token=bearer, wait_on_rate_limit=True)


def _leader_user_ids(client, leaders: list[Leader]) -> dict[str, str]:
    """Resolve X user IDs for leader handles."""
    handles = [leader.handle for leader in leaders]
    response = client.get_users(usernames=handles)
    if not response.data:
        return {}
    return {user.username.lower(): user.id for user in response.data}


def fetch_recent_tweets(
    leaders: list[Leader] | None = None,
    max_per_user: int = 50,
) -> pd.DataFrame:
    """
    Fetch recent tweets from leaders. Falls back to cache if no API key.

    Returns DataFrame with columns:
        tweet_id, handle, text, created_at, like_count, retweet_count
    """
    leaders = leaders or MARKET_LEADERS
    client = _get_twitter_client()

    if client is None:
        cached = load_cached_tweets()
        if not cached.empty:
            return cached
        raise RuntimeError(
            "No X_BEARER_TOKEN set and no cached tweets found. "
            "Set X_BEARER_TOKEN in .env or add tweets to data/tweets_cache.jsonl"
        )

    user_ids = _leader_user_ids(client, leaders)
    rows: list[dict] = []

    for leader in leaders:
        user_id = user_ids.get(leader.handle.lower())
        if not user_id:
            continue
        response = client.get_users_tweets(
            id=user_id,
            max_results=min(max_per_user, 100),
            tweet_fields=["created_at", "public_metrics", "lang"],
            exclude=["retweets", "replies"],
        )
        if not response.data:
            continue
        for tweet in response.data:
            metrics = tweet.public_metrics or {}
            rows.append(
                {
                    "tweet_id": str(tweet.id),
                    "handle": leader.handle,
                    "text": tweet.text,
                    "created_at": tweet.created_at,
                    "like_count": metrics.get("like_count", 0),
                    "retweet_count": metrics.get("retweet_count", 0),
                    "reply_count": metrics.get("reply_count", 0),
                }
            )

    df = pd.DataFrame(rows)
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
        cache_tweets(df)
    return df


def cache_tweets(df: pd.DataFrame) -> None:
    """Append tweets to local JSONL cache for offline backtesting."""
    _ensure_data_dir()
    existing_ids = set()
    if TWEET_CACHE.exists():
        with open(TWEET_CACHE) as f:
            for line in f:
                existing_ids.add(json.loads(line)["tweet_id"])

    with open(TWEET_CACHE, "a") as f:
        for _, row in df.iterrows():
            if row["tweet_id"] in existing_ids:
                continue
            record = row.to_dict()
            record["created_at"] = record["created_at"].isoformat()
            f.write(json.dumps(record) + "\n")


def load_cached_tweets(since: datetime | None = None) -> pd.DataFrame:
    """Load tweets from local cache."""
    if not TWEET_CACHE.exists():
        return pd.DataFrame()

    rows = []
    with open(TWEET_CACHE) as f:
        for line in f:
            rows.append(json.loads(line))

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    if since is not None:
        since = since.replace(tzinfo=timezone.utc) if since.tzinfo is None else since
        df = df[df["created_at"] >= since]
    return df.sort_values("created_at").reset_index(drop=True)


def import_tweets_csv(path: str | Path) -> pd.DataFrame:
    """
    Import tweets from a CSV with columns: handle, text, created_at.
    Optional: tweet_id, like_count, retweet_count.
    """
    df = pd.read_csv(path)
    required = {"handle", "text", "created_at"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")

    if "tweet_id" not in df.columns:
        df["tweet_id"] = range(len(df))
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    cache_tweets(df)
    return df
