"""Parse user-pasted Grok responses into structured market signals."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Default watchlist
DEFAULT_TICKERS = [
    "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "AMD",
]

BULLISH_WORDS = {
    "bullish", "rally", "surge", "moon", "buy", "beat", "upgrade", "growth",
    "strong", "breakout", "optimistic", "recovery", "outperform", "upside",
}
BEARISH_WORDS = {
    "bearish", "crash", "selloff", "sell", "downgrade", "miss", "weak",
    "recession", "warning", "risk", "concern", "underperform", "downside", "hawkish",
}


@dataclass
class TickerSignal:
    ticker: str
    sentiment: float  # -1 to +1
    reason: str
    source: str  # grok_parse | keyword | explicit_score
    mentions: int = 0


@dataclass
class GrokBriefing:
    raw_text: str
    overall_mood: float
    overall_label: str
    themes: list[str]
    tickers: dict[str, TickerSignal]
    top_movers: list[TickerSignal]
    tier1_voices: list[str]
    risks: list[str]
    explicit_direction: str | None = None


_SCORE_RE = re.compile(
    r"(?:^|\n)\s*(\$?)([A-Z]{1,5})\s*[:=\-]\s*([+-]?\d+\.?\d*)",
    re.MULTILINE | re.IGNORECASE,
)
_TICKER_MENTION = re.compile(r"\$([A-Z]{1,5})\b")
_SECTION_MOOD = re.compile(r"overall[:\s]*(bullish|bearish|neutral)", re.I)
_EXPLICIT_SCORE = re.compile(r"score[:\s]*([+-]?\d+\.?\d*)", re.I)
_DIRECTION_RE = re.compile(r"(?:OVERALL DIRECTION|PREDICTION)[:\s]*(UP|DOWN|FLAT)", re.I)
_CONFIDENCE_RE = re.compile(r"confidence[:\s]*(\d+)", re.I)


def _clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _keyword_sentiment(text: str) -> float:
    lower = text.lower()
    bull = sum(1 for w in BULLISH_WORDS if w in lower)
    bear = sum(1 for w in BEARISH_WORDS if w in lower)
    if bull + bear == 0:
        return 0.0
    return _clamp((bull - bear) / max(bull + bear, 1))


def _parse_ticker_scores(text: str) -> dict[str, TickerSignal]:
    signals: dict[str, TickerSignal] = {}
    for m in _SCORE_RE.finditer(text):
        ticker = m.group(2).upper()
        try:
            score = _clamp(float(m.group(3)))
        except ValueError:
            continue
        line_end = text.find("\n", m.end())
        reason = text[m.end() : line_end if line_end != -1 else m.end() + 80].strip(" -—:")
        signals[ticker] = TickerSignal(
            ticker=ticker,
            sentiment=score,
            reason=reason[:120] or "Explicit score from Grok",
            source="explicit_score",
        )
    return signals


def _parse_movers_section(text: str) -> list[TickerSignal]:
    movers = []
    section = ""
    if "TOP MOVERS" in text.upper():
        idx = text.upper().find("TOP MOVERS")
        section = text[idx : idx + 1500]
    elif "BULLISH BUZZ" in text.upper():
        idx = text.upper().find("BULLISH BUZZ")
        section = text[idx : idx + 2000]
    else:
        section = text

    for line in section.split("\n"):
        tickers = _TICKER_MENTION.findall(line.upper())
        if not tickers:
            continue
        ticker = tickers[0]
        sent = _keyword_sentiment(line)
        movers.append(TickerSignal(
            ticker=ticker,
            sentiment=sent,
            reason=line.strip()[:120],
            source="mover_parse",
            mentions=1,
        ))
    return movers[:10]


def _parse_themes(text: str) -> list[str]:
    themes = []
    for line in text.split("\n"):
        if "theme" in line.lower() or "key theme" in line.lower():
            parts = re.split(r"[:,]", line, maxsplit=1)
            if len(parts) > 1:
                for t in re.split(r"[,;•\-]", parts[1]):
                    t = t.strip()
                    if t and len(t) > 3:
                        themes.append(t[:80])
    return themes[:5]


def _parse_risks(text: str) -> list[str]:
    risks = []
    if "RISK" in text.upper():
        idx = text.upper().find("RISK")
        block = text[idx : idx + 600]
        for line in block.split("\n")[1:6]:
            line = line.strip(" -•123456789.")
            if line and len(line) > 5:
                risks.append(line[:100])
    return risks


def parse_grok_paste(text: str, watchlist: list[str] | None = None) -> GrokBriefing:
    """Extract structured signals from pasted Grok response."""
    watchlist = watchlist or DEFAULT_TICKERS
    text = text.strip()

    # Overall mood
    mood_match = _SECTION_MOOD.search(text)
    mood_label = mood_match.group(1).lower() if mood_match else "neutral"
    mood_score = {"bullish": 0.4, "bearish": -0.4, "neutral": 0.0}.get(mood_label, 0.0)
    score_m = _EXPLICIT_SCORE.search(text[:500])
    if score_m:
        mood_score = _clamp(float(score_m.group(1)))

    # Explicit scores per ticker
    tickers = _parse_ticker_scores(text)

    # Fill watchlist tickers from keyword context if no explicit score
    for ticker in watchlist:
        if ticker in tickers:
            continue
        pattern = re.compile(rf"\$?{ticker}\b", re.I)
        mentions = len(pattern.findall(text))
        if mentions == 0:
            continue
        # Grab surrounding context for each mention
        contexts = []
        for m in pattern.finditer(text):
            start = max(0, m.start() - 80)
            end = min(len(text), m.end() + 80)
            contexts.append(text[start:end])
        combined = " ".join(contexts)
        tickers[ticker] = TickerSignal(
            ticker=ticker,
            sentiment=_keyword_sentiment(combined),
            reason=f"Mentioned {mentions}x in Grok briefing",
            source="keyword",
            mentions=mentions,
        )

    top_movers = _parse_movers_section(text)
    direction_m = _DIRECTION_RE.search(text)

    return GrokBriefing(
        raw_text=text,
        overall_mood=mood_score,
        overall_label=mood_label,
        themes=_parse_themes(text),
        tickers=tickers,
        top_movers=top_movers,
        tier1_voices=[],
        risks=_parse_risks(text),
        explicit_direction=direction_m.group(1).upper() if direction_m else None,
    )
