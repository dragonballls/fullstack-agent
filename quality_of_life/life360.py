"""Authorized Life360 family-location adapter through Home Assistant.

Life360 does not expose a documented public consumer API for arbitrary desktop
clients, so Jarvis uses the Home Assistant Life360 integration as the concrete
transport. Only entities already exposed to the user's Home Assistant instance
are read; Jarvis never attempts to log into Life360 directly or bypass sharing.

Configuration:
  JARVIS_LIFE360_ENABLED=1
  JARVIS_LIFE360_HA_URL=http://127.0.0.1:8123
  JARVIS_LIFE360_HA_TOKEN=<Home Assistant long-lived access token>

Optional:
  JARVIS_LIFE360_ENTITY_IDS=device_tracker.alice,device_tracker.bob

Without explicit enablement and credentials the provider stays unavailable.
"""

from __future__ import annotations

import ipaddress
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from .gods_eye import GeoPoint

DEFAULT_HA_URL = "http://127.0.0.1:8123"
DEFAULT_TIMEOUT_SECONDS = 5.0


class Life360HomeAssistantProvider:
    """Read authorized Life360 device_tracker entities from Home Assistant."""

    name = "life360"

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        *,
        enabled: bool | None = None,
        fetch_json: Callable[[str, str], Any] | None = None,
        entity_ids: tuple[str, ...] | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("JARVIS_LIFE360_HA_URL") or DEFAULT_HA_URL).rstrip("/")
        self.token = token if token is not None else os.environ.get("JARVIS_LIFE360_HA_TOKEN", "")
        self.enabled = (
            enabled
            if enabled is not None
            else os.environ.get("JARVIS_LIFE360_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
        )
        self._fetch_json = fetch_json or self._request_json
        configured_ids = entity_ids
        if configured_ids is None:
            configured_ids = tuple(
                item.strip() for item in os.environ.get("JARVIS_LIFE360_ENTITY_IDS", "").split(",") if item.strip()
            )
        self.entity_ids = frozenset(configured_ids)

    def _configured(self) -> bool:
        return bool(self.enabled and self.token.strip() and self._safe_base_url())

    def _safe_base_url(self) -> bool:
        try:
            parsed = urllib.parse.urlparse(self.base_url)
            if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or not parsed.hostname:
                return False
            host = parsed.hostname.casefold()
            if host in {"localhost", "homeassistant", "home-assistant"} or host.endswith(".local"):
                return True
            try:
                return ipaddress.ip_address(host).is_private or ipaddress.ip_address(host).is_loopback
            except ValueError:
                return False
        except ValueError:
            return False

    def status(self) -> dict[str, Any]:
        if not self.enabled:
            return {
                "available": False,
                "authorized": False,
                "live": False,
                "source": self.name,
                "detail": "Life360 integration is disabled",
            }
        if not self.token.strip():
            return {
                "available": False,
                "authorized": False,
                "live": False,
                "source": self.name,
                "detail": "Home Assistant access token is not configured",
            }
        if not self._safe_base_url():
            return {
                "available": False,
                "authorized": False,
                "live": False,
                "source": self.name,
                "detail": "Home Assistant URL must point to a local/private or .local host",
            }
        try:
            payload = self._fetch_json(self._url("/api/"), self.token)
            available = isinstance(payload, dict) and str(payload.get("message", "")).strip().lower() == "api running."
            return {
                "available": available,
                "authorized": available,
                "live": available,
                "source": self.name,
                "detail": "Home Assistant Life360 states available" if available else "Home Assistant API did not report ready",
            }
        except _Unauthorized:
            return {
                "available": False,
                "authorized": False,
                "live": False,
                "source": self.name,
                "detail": "Home Assistant authorization failed",
            }
        except Exception as exc:
            return {
                "available": False,
                "authorized": False,
                "live": False,
                "source": self.name,
                "detail": f"Home Assistant Life360 unavailable ({type(exc).__name__})",
            }

    def locations(self) -> list[dict[str, object]]:
        state = self.status()
        if not (state["available"] and state["authorized"] and state["live"]):
            return []
        try:
            payload = self._fetch_json(self._url("/api/states"), self.token)
        except Exception:
            return []
        if not isinstance(payload, list):
            return []

        locations: list[dict[str, object]] = []
        for item in payload:
            parsed = self._normalize_state(item)
            if parsed is not None:
                locations.append(parsed)
        return locations[:100]

    def _normalize_state(self, item: object) -> dict[str, object] | None:
        if not isinstance(item, dict):
            return None
        entity_id = str(item.get("entity_id", "")).strip()
        if not entity_id.startswith("device_tracker."):
            return None
        if self.entity_ids and entity_id not in self.entity_ids:
            return None
        attrs = item.get("attributes")
        if not isinstance(attrs, dict):
            return None
        attribution = str(attrs.get("attribution", "")).strip()
        if self.entity_ids:
            is_life360 = True
        else:
            is_life360 = "life360.com" in attribution.casefold() or "life360" in entity_id.casefold()
        if not is_life360:
            return None

        try:
            point = GeoPoint(float(attrs["latitude"]), float(attrs["longitude"]))
        except (KeyError, TypeError, ValueError):
            return None

        name = str(attrs.get("friendly_name") or entity_id.removeprefix("device_tracker.")).strip()
        if not name:
            return None

        location: dict[str, object] = {
            "id": entity_id,
            "name": name,
            "point": point.as_dict(),
            "source": self.name,
            "provider": self.name,
            "state": str(item.get("state", "")),
        }
        for output_key, candidates in {
            "accuracy_m": ("gps_accuracy",),
            "battery_level": ("battery_level", "battery"),
            "address": ("address",),
            "place": ("place",),
            "last_seen": ("last_seen",),
            "driving": ("driving",),
            "battery_charging": ("battery_charging",),
        }.items():
            for candidate in candidates:
                if attrs.get(candidate) is not None:
                    location[output_key] = attrs[candidate]
                    break
        return location

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    @staticmethod
    def _request_json(url: str, token: str) -> Any:
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:  # nosec B310: base URL is validated before use
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise _Unauthorized from exc
            raise


class _Unauthorized(RuntimeError):
    pass
