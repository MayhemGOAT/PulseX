"""Live alert helpers — notify when tier-1 leaders post."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from event_detector import MarketEvent, detect_events
from leaders import LEADER_BY_HANDLE


ALERT_LOG = Path(__file__).parent / "data" / "alerts.jsonl"


def check_for_alerts(scored_tweets, min_weight: float = 0.85) -> list[MarketEvent]:
    """Return new high-impact events not yet logged."""
    events = detect_events(scored_tweets, min_weight=min_weight)
    seen = _load_seen_ids()
    new_events = []
    for event in events:
        eid = _event_id(event)
        if eid not in seen:
            new_events.append(event)
            _log_alert(event, eid)
    return new_events


def _event_id(event: MarketEvent) -> str:
    return f"{event.date}|{event.leader}|{hash(event.text) % 10**8}"


def _load_seen_ids() -> set[str]:
    if not ALERT_LOG.exists():
        return set()
    ids = set()
    with open(ALERT_LOG) as f:
        for line in f:
            record = json.loads(line)
            ids.add(record.get("id", ""))
    return ids


def _log_alert(event: MarketEvent, eid: str) -> None:
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "id": eid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "leader": event.leader,
        "impact_score": event.impact_score,
        "event_type": event.event_type,
        "text": event.text,
    }
    with open(ALERT_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")


def format_alert(event: MarketEvent) -> str:
    leader = LEADER_BY_HANDLE.get(event.leader.lower())
    name = leader.name if leader else event.leader
    tone = "BULLISH" if event.impact_score > 0 else "BEARISH"
    return (
        f"🚨 TIER-1 ALERT — {name}\n"
        f"Impact: {event.impact_score:+.3f} ({tone})\n"
        f"Type: {event.event_type}\n"
        f"\"{event.text[:120]}\""
    )
