"""Location and geocoding providers for God’s Eye."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from .gods_eye import GeoPoint, LocationSnapshot, Place


class NominatimGeocoder:
    """Small HTTPS-only OpenStreetMap Nominatim adapter with bounded requests."""

    def __init__(
        self,
        endpoint: str = "https://nominatim.openstreetmap.org/search",
        fetch_json: Callable[[str], Any] | None = None,
        user_agent: str = "fullstack-agent-gods-eye/1.0",
    ) -> None:
        self.endpoint = endpoint
        self._fetch_json = fetch_json or self._request_json
        self.user_agent = user_agent

    def search(self, query: str) -> list[Place]:
        params = urllib.parse.urlencode({"q": query, "format": "jsonv2", "limit": 5})
        url = f"{self.endpoint}?{params}"
        if not url.startswith("https://"):
            raise ValueError("God’s Eye geocoder endpoint must use HTTPS")
        try:
            rows = self._fetch_json(url)
        except (OSError, ValueError, TimeoutError):
            return []
        if not isinstance(rows, list):
            return []
        places: list[Place] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                name = str(row["display_name"]).strip()
                point = GeoPoint(float(row["lat"]), float(row["lon"]))
            except (KeyError, TypeError, ValueError):
                continue
            places.append(Place(name, point, str(row.get("osm_id")) if row.get("osm_id") is not None else None, "nominatim"))
        return places

    def _request_json(self, url: str) -> Any:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(request, timeout=5) as response:  # nosec B310: URL is explicitly HTTPS-validated
            return json.load(response)


class SystemLocationProvider:
    """Explicit location-provider boundary; no silent precise-location access."""

    def __init__(self, get_location: Callable[[], LocationSnapshot] | None = None) -> None:
        self._get_location = get_location

    def current(self) -> LocationSnapshot:
        if self._get_location is None:
            return LocationSnapshot(None, None, False, "unavailable")
        try:
            snapshot = self._get_location()
        except Exception:
            return LocationSnapshot(None, None, False, "error")
        if not isinstance(snapshot, LocationSnapshot):
            return LocationSnapshot(None, None, False, "invalid")
        return snapshot
