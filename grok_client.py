"""xAI Grok API client — OpenAI-compatible chat completions."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

XAI_BASE_URL = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-3-mini"


def is_available() -> bool:
    return bool(os.getenv("XAI_API_KEY"))


def _model() -> str:
    return os.getenv("PULSEX_GROK_MODEL", DEFAULT_MODEL)


def _parse_json_content(content: str) -> dict:
    """Extract JSON object from Grok response (handles markdown fences)."""
    content = content.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if fence:
        content = fence.group(1)
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object in response: {content[:200]}")
    return json.loads(content[start : end + 1])


def chat(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.2,
    timeout: int = 60,
) -> str | None:
    """Send chat completion to Grok. Returns assistant text or None if unavailable."""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        return None

    payload = json.dumps({
        "model": model or _model(),
        "messages": messages,
        "temperature": temperature,
    }).encode()

    req = urllib.request.Request(
        f"{XAI_BASE_URL}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError):
        return None


def chat_json(
    system: str,
    user: str,
    model: str | None = None,
) -> dict | None:
    """Chat and parse JSON object from response."""
    content = chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=model,
    )
    if not content:
        return None
    try:
        return _parse_json_content(content)
    except (ValueError, json.JSONDecodeError):
        return None


def score_tweet_impact(
    text: str,
    leader_handle: str,
    leader_name: str,
    ticker: str = "SPY",
) -> dict | None:
    """Ask Grok to score a single leader tweet for market impact."""
    system = (
        "You are Grok, a financial markets analyst. "
        "Score how a leader's X/Twitter post affects US stock prices. "
        "Respond with JSON only — no markdown."
    )
    user = f"""Leader: {leader_name} (@{leader_handle})
Target ticker: {ticker}
Tweet: "{text}"

Return JSON:
{{
  "market_impact": <float -1 to 1, bearish to bullish>,
  "reasoning": "<one sentence>",
  "affected_tickers": ["<tickers>"],
  "urgency": "<low|medium|high>"
}}"""

    return chat_json(system, user)


def analyze_market(
    ticker: str,
    price_summary: dict,
    tweets: list[dict],
) -> dict | None:
    """Ask Grok for holistic market read from price + leader tweets."""
    if not tweets:
        return None

    tweet_lines = "\n".join(
        f"- @{t.get('handle', '?')}: {str(t.get('text', ''))[:200]}"
        for t in tweets[:15]
    )
    system = (
        "You are Grok, senior market strategist on the PulseX AI Council. "
        "Synthesize leader X posts and price context into a trading signal. "
        "Respond with JSON only."
    )
    user = f"""Ticker: {ticker}
Price context: {json.dumps(price_summary)}

Recent leader posts:
{tweet_lines}

Return JSON:
{{
  "direction": <float -1 bearish to +1 bullish>,
  "confidence": <float 0 to 1>,
  "reasoning": "<2-3 sentences>",
  "key_risk": "<main risk factor>"
}}"""

    return chat_json(system, user)
