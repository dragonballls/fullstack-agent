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
_SAVE_CURRENT = re.compile(r"^save\s+(?:my\s+current\s+location|this\s+location)\s+as\s+(.+)$", re.IGNORECASE)
_SAVE_PLACE = re.compile(r"^save\s+(.+?)\s+as\s+(.+)$", re.IGNORECASE)
_GET_SAVED = re.compile(r"^(?:go|route|navigate)\s+(?:me\s+)?to\s+my\s+(.+)$", re.IGNORECASE)
_DELETE_SAVED = re.compile(r"^(?:delete|forget|remove)\s+(?:my\s+)?saved\s+location\s+(.+)$", re.IGNORECASE)
_MOVE = re.compile(r"^move mouse to\s+(-?\d+)\s+(-?\d+)$", re.IGNORECASE)
_BROWSER = re.compile(r"^(?:open|use|launch)\s+(edge|microsoft edge|ms edge|chrome|google chrome|firefox|mozilla firefox|opera|opera gx|operagx|brave|brave browser|vivaldi)(?:\s+(?:and\s+)?(?:go to|open)\s+(https?://\S+))?$", re.IGNORECASE)
_FILE_DELETE = re.compile(r"^(?:delete\s+(?:file\s+)?|remove\s+file\s+)(.+)$", re.IGNORECASE)
_APP_UNINSTALL = re.compile(r"^(?:uninstall|remove\s+(?:the\s+)?(?:program|application|app))\s+(.+)$", re.IGNORECASE)
_MAINTENANCE = re.compile(r"^(?:diagnose|check|repair|fix|optimize|clean up|stop|prevent|disable).*(?:pc|computer|windows|steam|startup|background|cpu|ram|gpu|network|system files)", re.IGNORECASE)


def parse_intent(text: str) -> Intent:
    value = text.strip()
    if not value:
        return Intent("chat", {"text": ""})
    lowered = value.casefold()
    if lowered in {"where am i", "what is my location", "what's my location", "where are we"}:
        return Intent("locate_me", {})
    match = _SAVE_CURRENT.match(value)
    if match:
        return Intent("save_current_location", {"name": match.group(1).strip()})
    match = _DELETE_SAVED.match(value)
    if match:
        return Intent("delete_saved_location", {"name": match.group(1).strip()})
    match = _GET_SAVED.match(value)
    if match:
        return Intent("saved_location", {"name": match.group(1).strip()})
    match = _SAVE_PLACE.match(value)
    if match and not lowered.startswith("save my "):
        return Intent("save_place", {"place": match.group(1).strip(), "name": match.group(2).strip()})
    match = _MOVE.match(value)
    if match:
        return Intent("computer_action", {"operation": "move", "x": int(match.group(1)), "y": int(match.group(2))})
    match = _BROWSER.match(value)
    if match:
        return Intent("browser_open", {"browser": match.group(1), "url": match.group(2)})
    if _MAINTENANCE.match(value):
        return Intent("windows_maintenance", {"request": value})
    match = _FILE_DELETE.match(value)
    if match:
        return Intent("file_delete", {"path": match.group(1).strip()})
    match = _APP_UNINSTALL.match(value)
    if match:
        return Intent("application_uninstall", {"name": match.group(1).strip()})
    if lowered in {"list installed programs", "show installed programs", "what programs are installed"}:
        return Intent("application_list", {})
    if lowered in {"list processes", "show running processes", "what is running"}:
        return Intent("process_list", {})
    if lowered in {"system info", "system information", "check my system"}:
        return Intent("system_inspect", {})
    if lowered.startswith("read file "):
        return Intent("file_read", {"path": value.split(None, 2)[2].strip()})
    match = _ROUTE.match(value)
    if match:
        return Intent("route", {"query": match.group(1).strip()})
    match = _PLACE.match(value)
    if match:
        return Intent("place_search", {"query": match.group(1).strip()})
    if lowered in {"look at my screen", "what is on my screen", "read my screen"}:
        return Intent("screen_read", {})
    return Intent("chat", {"text": value})
