"""Authorized family-location data contracts and God’s Eye follow state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
from threading import RLock
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class FamilyLocationProvider(Protocol):
    def fetch(self) -> tuple["FamilyLocation", ...]: ...


def _utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("location timestamp must be an ISO datetime")
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


@dataclass(frozen=True)
class FamilyLocation:
    member_id: str
    name: str
    latitude: float
    longitude: float
    accuracy_m: float | None
    source: str
    observed_at: datetime
    sharing_state: str = "on"
    stale_after_seconds: int = 300

    def __post_init__(self) -> None:
        if not self.member_id.strip():
            raise ValueError("family member id is required")
        if not self.name.strip():
            raise ValueError("family member name is required")
        if not -90 <= float(self.latitude) <= 90:
            raise ValueError("latitude is out of range")
        if not -180 <= float(self.longitude) <= 180:
            raise ValueError("longitude is out of range")
        if self.accuracy_m is not None and float(self.accuracy_m) < 0:
            raise ValueError("accuracy must be non-negative")
        if self.sharing_state not in {"on", "paused", "unavailable", "unknown"}:
            raise ValueError("unsupported sharing state")
        object.__setattr__(self, "member_id", self.member_id.strip())
        object.__setattr__(self, "name", " ".join(self.name.split()))
        object.__setattr__(self, "latitude", float(self.latitude))
        object.__setattr__(self, "longitude", float(self.longitude))
        object.__setattr__(self, "accuracy_m", float(self.accuracy_m) if self.accuracy_m is not None else None)
        object.__setattr__(self, "source", self.source.strip() or "unknown")
        object.__setattr__(self, "observed_at", _utc(self.observed_at))
        object.__setattr__(self, "stale_after_seconds", max(1, int(self.stale_after_seconds)))

    @property
    def stale(self) -> bool:
        return datetime.now(timezone.utc) - self.observed_at > timedelta(seconds=self.stale_after_seconds)

    @property
    def available(self) -> bool:
        return self.sharing_state == "on"

    def as_dict(self) -> dict[str, object]:
        return {
            "member_id": self.member_id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy_m": self.accuracy_m,
            "source": self.source,
            "observed_at": self.observed_at.isoformat(),
            "sharing_state": self.sharing_state,
            "stale": self.stale,
            "available": self.available,
        }


class Life360LocationAdapter:
    """Normalize data supplied by an authorized Life360 bridge/feed.

    This class deliberately accepts a caller-supplied payload instead of
    reverse-engineering or scraping Life360's private application services.
    """

    def __init__(self, source_name: str = "life360") -> None:
        self.source_name = source_name

    def normalize(self, payload: dict[str, Any]) -> tuple[FamilyLocation, ...]:
        if not isinstance(payload, dict):
            raise ValueError("family location payload must be an object")
        members = payload.get("members")
        if not isinstance(members, list):
            raise ValueError("family location payload must contain members")
        result: list[FamilyLocation] = []
        for raw in members:
            if not isinstance(raw, dict):
                raise ValueError("family member must be an object")
            try:
                member_id = str(raw["id"])
                name = str(raw["name"])
                latitude = float(raw["latitude"])
                longitude = float(raw["longitude"])
                observed_at = _utc(raw["updated_at"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("family member is missing valid location fields") from exc
            sharing = str(raw.get("sharing", "on")).strip().casefold()
            if sharing in {"false", "off", "paused", "location sharing paused"}:
                sharing = "paused"
            elif sharing not in {"on", "true", "available"}:
                sharing = "unknown"
            result.append(
                FamilyLocation(
                    member_id=member_id,
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    accuracy_m=float(raw["accuracy_m"]) if raw.get("accuracy_m") is not None else None,
                    source=self.source_name,
                    observed_at=observed_at,
                    sharing_state=sharing,
                    stale_after_seconds=int(raw.get("stale_after_seconds", payload.get("stale_after_seconds", 300))),
                )
            )
        return tuple(result)


class Life360BridgeProvider:
    """Fetch JSON from an explicitly configured local/authorized bridge."""

    def __init__(self, url: str, *, timeout_s: float = 5.0, opener: Callable[..., Any] = urlopen) -> None:
        if not url.strip().startswith(("http://", "https://")):
            raise ValueError("family location bridge URL must be HTTP(S)")
        self.url = url.strip()
        self.timeout_s = max(1.0, float(timeout_s))
        self._opener = opener
        self.adapter = Life360LocationAdapter()

    def fetch(self) -> tuple[FamilyLocation, ...]:
        request = Request(self.url, headers={"Accept": "application/json", "User-Agent": "Jarvis-FamilyLocation/1.0"})
        try:
            with self._opener(request, timeout=self.timeout_s) as response:
                raw = response.read(2_000_000)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"family location bridge unavailable: {type(exc).__name__}") from exc
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("family location bridge returned invalid JSON") from exc
        return self.adapter.normalize(payload)


class FamilyLocationService:
    """Maintain latest authorized family positions and a selected follow target."""

    def __init__(self, provider: FamilyLocationProvider | None = None) -> None:
        self.provider = provider
        self._locations: dict[str, FamilyLocation] = {}
        self._aliases: dict[str, set[str]] = {}
        self._follow_member_id: str | None = None
        self._lock = RLock()

    def apply(self, locations: list[FamilyLocation] | tuple[FamilyLocation, ...]) -> bool:
        changed = False
        with self._lock:
            for location in locations:
                current = self._locations.get(location.member_id)
                if current is not None and location.observed_at <= current.observed_at:
                    continue
                self._locations[location.member_id] = location
                key = " ".join(location.name.casefold().split())
                self._aliases.setdefault(key, set()).add(location.member_id)
                changed = True
        return changed

    def refresh(self) -> int:
        if self.provider is None:
            raise RuntimeError("family location provider is not configured")
        locations = self.provider.fetch()
        self.apply(locations)
        return len(locations)

    def members(self) -> tuple[FamilyLocation, ...]:
        with self._lock:
            return tuple(sorted(self._locations.values(), key=lambda item: item.name.casefold()))

    def get(self, reference: str) -> FamilyLocation:
        value = reference.strip()
        if not value:
            raise ValueError("family member reference is required")
        with self._lock:
            exact = self._locations.get(value)
            if exact is not None:
                return exact
            matches = self._aliases.get(" ".join(value.casefold().split()), set())
            if len(matches) > 1:
                raise ValueError(f"multiple family members match: {value}")
            if len(matches) == 1:
                return self._locations[next(iter(matches))]
        raise LookupError(f"family member not found: {value}")

    def follow(self, reference: str) -> FamilyLocation:
        member = self.get(reference)
        with self._lock:
            self._follow_member_id = member.member_id
        return member

    def stop_follow(self) -> None:
        with self._lock:
            self._follow_member_id = None

    def following(self) -> FamilyLocation | None:
        with self._lock:
            if self._follow_member_id is None:
                return None
            return self._locations.get(self._follow_member_id)

    def followed_location(self) -> FamilyLocation | None:
        return self.following()

    def map_state(self) -> dict[str, object]:
        with self._lock:
            following = self._locations.get(self._follow_member_id) if self._follow_member_id else None
            markers = [location.as_dict() for location in sorted(self._locations.values(), key=lambda item: item.name.casefold())]
            return {
                "surface": "gods-eye",
                "family_markers": markers,
                "follow_member_id": self._follow_member_id,
                "follow_center": {
                    "latitude": following.latitude,
                    "longitude": following.longitude,
                } if following and following.available else None,
            }

    @staticmethod
    def stale_from_fixture(member_id: str, name: str, latitude: float, longitude: float, *, observed_at: datetime) -> FamilyLocation:
        return FamilyLocation(member_id, name, latitude, longitude, None, "fixture", observed_at, "on", 1)


def configured_life360_provider() -> Life360BridgeProvider | None:
    url = os.environ.get("JARVIS_LIFE360_BRIDGE_URL", "").strip()
    return Life360BridgeProvider(url) if url else None
