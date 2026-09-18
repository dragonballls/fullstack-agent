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
_HAND_START = re.compile(r"^(?:turn\s+on|enable|start)\s+(?:webcam\s+)?hand\s+control$|^(?:enable|start)\s+(?:webcam\s+)?control$", re.IGNORECASE)
_HAND_STOP = re.compile(r"^(?:turn\s+off|disable|stop|pause)\s+(?:webcam\s+)?hand\s+control$|^(?:disable|stop)\s+(?:webcam\s+)?control$", re.IGNORECASE)
_DEVICE_HAND = re.compile(r"^(?:use|send|route|target|control)\s+(?:webcam\s+|my\s+)?(?:hand\s+control|hands?)\s+(?:on|for|to)\s+(?:my\s+)?(?:phone|device)(?:\s+(.+))?$", re.IGNORECASE)
_DEVICE_LIST = re.compile(r"^(?:list|show)(?:\s+me)?\s+(?:my\s+)?(?:phones|devices)$", re.IGNORECASE)
_DEVICE_REFRESH = re.compile(r"^(?:refresh|scan|find)\s+(?:my\s+)?(?:phones|devices)$", re.IGNORECASE)
_DEVICE_SELECT = re.compile(r"^(?:switch to|select|use)\s+(?:my\s+)?(?:phone|device)(?:\s+(.+))$|^(?:switch to|select|use)\s+(.+?)(?:\s+phone)?$", re.IGNORECASE)
_DEVICE_SCREEN_ALL = re.compile(r"^(?:show|view|mirror)\s+(?:me\s+)?(?:all|both)\s+(?:my\s+)?(?:phone|phones|device|devices)(?:\s+(?:screen|screens|view|views))?$", re.IGNORECASE)
_DEVICE_SCREEN = re.compile(r"^(?:show|view)\s+(?:me\s+)?(?:(?:my|the)\s+)?(?:phone|device)(?:\s+(.+?))?(?:\s+(?:screen|view))?$", re.IGNORECASE)
_OBSERVE_START = re.compile(r"^(?:show(?:\s+me)?|let\s+me\s+see|walk\s+me\s+through|take\s+me\s+through)\s+(?:what\s+(?:you['’]?re|you\s+are)\s+doing|your\s+process|the\s+process|what\s+you\s+are\s+working\s+on)(?:\s+(.+))?$", re.IGNORECASE)
_OBSERVE_STOP = re.compile(r"^(?:stop|hide|close)\s+(?:the\s+)?(?:live\s+)?(?:process|observation|activity\s+view)$|^(?:stop|hide)\s+showing\s+me\s+(?:what\s+you['’]?re|what\s+you\s+are)\s+doing$", re.IGNORECASE)
_SHAPE = re.compile(r"^(?:make|turn|change)\s+(?:the\s+)?(.+?)\s+(?:neuron|node)?\s*(?:into|as)\s+(.+)$", re.IGNORECASE)
_SHAPE_REVERT_ALL = re.compile(r"^(?:revert|restore|reset)\s+(?:everything|all)\s+(?:to\s+)?(?:the\s+)?(?:original|original\s+state)(?:\s+state)?$", re.IGNORECASE)
_SHAPE_REVERT = re.compile(r"^(?:revert|restore|reset)\s+(?:the\s+)?(.+?)(?:\s+to\s+)?(?:its\s+)?original(?:\s+state)?$", re.IGNORECASE)
_SHAPE_REMOVE = re.compile(r"^(?:remove|delete)\s+(?:it|this\s+(?:object|shape|neuron|node|surface|tab|window)|the\s+(?:object|shape|neuron|node|surface|tab|window))$", re.IGNORECASE)
_SHAPE_CREATE = re.compile(r"^(?:create|generate|build|make)\s+(?:a|an|the)?\s*(.+?)(?:\s+(?:called|named)\s+(.+))?$", re.IGNORECASE)
_SHAPE_APPLY = re.compile(r"^(?:make|turn|change|reshape)\s+(.+?)\s+(?:into|as|to|the shape of)\s+(?:a|an|the)?\s*(.+)$", re.IGNORECASE)
_ROTATION_SPEED = re.compile(r"^(.*?)\s+and\s+(?:give|set)\s+(?:it\s+)?(?:a\s+)?(?:rotational|rotation|angular)\s+speed\s+(-?\d+(?:\.\d+)?)\s*(rpm|rps|degrees?\s*(?:per|/)\s*second|rad(?:ian)?s?\s*(?:per|/)\s*second)?(?:\s+(?:around|on)\s+([xyz]|xyz))?\s*$", re.IGNORECASE)

_SHAPE_SAVE = re.compile(r"^(?:save|remember)\s+(?:this\s+)?shape\s+(.+?)\s+(?:as|named)\s+(.+)$", re.IGNORECASE)
_SPATIAL_OPEN = re.compile(r"^(?:open|launch|start|put)\s+(?:the\s+)?(.+?)\s+(?:in|inside|within)\s+(?:the\s+)?(?:3d\s+)?(?:space|spatial\s+space|jarvis\s+space|neural\s+space)$", re.IGNORECASE)


def parse_intent(text: str) -> Intent:
    value = text.strip()
    if not value:
        return Intent("chat", {"text": ""})
    lowered = value.casefold()
    match = _SPATIAL_OPEN.match(value)
    if match:
        return Intent("spatial_open", {"application": match.group(1).strip()})
    match = _OBSERVE_START.match(value)
    if match:
        return Intent("neural_observe_start", {"focus": (match.group(1) or "").strip() or "auto", "reason": value})
    if _OBSERVE_STOP.match(value):
        return Intent("neural_observe_stop", {})
    match = _SHAPE_SAVE.match(value)
    if match:
        return Intent("neural_shape_save", {"shape": match.group(1).strip(), "name": match.group(2).strip()})
    if _SHAPE_REVERT_ALL.match(value) or lowered in {"revert everything", "restore everything", "reset all shapes", "restore original state"}:
        return Intent("neural_shape_revert_all", {})
    match = _SHAPE_REVERT.match(value)
    if match:
    if _SHAPE_REMOVE.match(value):
        return Intent("neural_shape_remove", {})
        return Intent("neural_shape_revert", {"target": match.group(1).strip()})
    match = _SHAPE_APPLY.match(value)
    if match:
        target = match.group(1).strip()
        requested_shape = match.group(2).strip()
        rotation_speed = 0.0
        rotation_unit = None
        rotation_axis = "y"
        speed_match = _ROTATION_SPEED.match(requested_shape)
        if speed_match:
            requested_shape = speed_match.group(1).strip()
            rotation_speed = float(speed_match.group(2))
            rotation_unit = speed_match.group(3)
            rotation_axis = (speed_match.group(4) or "y").lower()
        requested_shape = re.sub(r"^(?:the\s+)?shape\s+of\s+", "", requested_shape, flags=re.IGNORECASE).strip()
        if requested_shape.casefold().startswith("a "):
            requested_shape = requested_shape[2:].strip()
        elif requested_shape.casefold().startswith("an "):
            requested_shape = requested_shape[3:].strip()
        return Intent("neural_shape", {"target": target, "shape": requested_shape, "rotation_speed": rotation_speed, "rotation_unit": rotation_unit, "rotation_axis": rotation_axis})
    match = _SHAPE_CREATE.match(value)
    if match:
        return Intent("neural_shape_create", {"shape": match.group(1).strip(), "name": (match.group(2) or "").strip()})
    if _HAND_START.match(value):
        return Intent("hand_control_start", {})
    if _HAND_STOP.match(value):
        return Intent("hand_control_stop", {})
    match = _DEVICE_HAND.match(value)
    if match:
        return Intent("device_hand_target", {"device": (match.group(1) or "").strip() or None})
    if _DEVICE_LIST.match(value):
        return Intent("device_list", {})
    if _DEVICE_REFRESH.match(value):
        return Intent("device_refresh", {})
    match = _DEVICE_SELECT.match(value)
    if match:
        return Intent("device_select", {"device": (match.group(1) or match.group(2) or "").strip()})
    if _DEVICE_SCREEN_ALL.match(value):
        return Intent("device_screen_all", {})
    match = _DEVICE_SCREEN.match(value)
    if match:
        label = (match.group(1) or "").strip()
        if label.casefold() in {"screen", "view"}:
            label = ""
        return Intent("device_screen", {"device": label or None})
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
        browser = match.group(1)
        url = match.group(2)
        return Intent("browser_open", {"browser": browser, "url": url})
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
