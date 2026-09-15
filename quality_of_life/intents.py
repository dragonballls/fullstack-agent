"""Conservative natural-language intent parsing; this layer never executes actions."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    kind: str
    arguments: dict[str, object]


_PLACE = re.compile(r"^(?:open|show(?: me)?|find)\s+(.+)$", re.IGNORECASE)
_ROUTE = re.compile(r"^(?:take|navigate|route)\s+(?:me\s+)?to\s+(.+)$", re.IGNORECASE)
_MOVE = re.compile(r"^move mouse to\s+(-?\d+)\s+(-?\d+)$", re.IGNORECASE)


def parse_intent(text: str) -> Intent:
    value = text.strip()
    if not value:
        return Intent("chat", {"text": ""})
    lowered = value.casefold()
    if lowered in {"where am i", "what is my location", "what's my location", "where are we"}:
        return Intent("locate_me", {})
    match = _MOVE.match(value)
    if match:
        return Intent("computer_action", {"operation": "move", "x": int(match.group(1)), "y": int(match.group(2))})
    match = _ROUTE.match(value)
    if match:
        return Intent("route", {"query": match.group(1).strip()})
    match = _PLACE.match(value)
    if match:
        return Intent("place_search", {"query": match.group(1).strip()})
    if lowered in {"look at my screen", "what is on my screen", "read my screen"}:
        return Intent("screen_read", {})
    return Intent("chat", {"text": value})
