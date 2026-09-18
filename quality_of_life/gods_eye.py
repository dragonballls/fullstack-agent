"""Pure God’s Eye location and map-context contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol
from urllib.parse import quote
from .location_providers import LocationProviderRegistry


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("latitude must be between -90 and 90")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("longitude must be between -180 and 180")

    def as_dict(self) -> dict[str, float]:
        return {"latitude": self.latitude, "longitude": self.longitude}


@dataclass(frozen=True)
class Place:
    name: str
    point: GeoPoint
    place_id: str | None
    provider: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("place name cannot be empty")
        if not self.provider.strip():
            raise ValueError("provider cannot be empty")

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "point": self.point.as_dict(),
            "place_id": self.place_id,
            "provider": self.provider,
        }


@dataclass(frozen=True)
class LocationSnapshot:
    point: GeoPoint | None
    accuracy_m: float | None
    permitted: bool
    source: str

    def __post_init__(self) -> None:
        if self.accuracy_m is not None and self.accuracy_m < 0:
            raise ValueError("accuracy_m cannot be negative")

    def as_dict(self) -> dict[str, object]:
        return {
            "point": self.point.as_dict() if self.point else None,
            "accuracy_m": self.accuracy_m,
            "permitted": self.permitted,
            "source": self.source,
        }


class Geocoder(Protocol):
    def search(self, query: str) -> list[Place]: ...


class LocationProvider(Protocol):
    def current(self) -> LocationSnapshot: ...


class GodsEye:
    """Single service boundary for place and location context."""

    def __init__(self, geocoder: Geocoder, location_provider: LocationProvider) -> None:
        self.geocoder = geocoder
        self.location_provider = location_provider
        self.provider_registry = LocationProviderRegistry()

    def search(self, query: str) -> list[Place]:
        normalized = query.strip()
        if not normalized:
            raise ValueError("location query cannot be empty")
        return self.geocoder.search(normalized)

    def register_location_provider(self, kind: str, provider: object) -> None:
        self.provider_registry.register(kind, provider)

    def provider_locations(self, kind: str) -> list[dict[str, object]]:
        return self.provider_registry.locations(kind)

    def locate_me(self) -> LocationSnapshot:
        return self.location_provider.current()

    def route(self, origin: GeoPoint, destination: Place) -> dict[str, object]:
        return {
            "provider": "openstreetmap",
            "origin": origin.as_dict(),
            "destination": destination.point.as_dict(),
            "navigation_url": (
                "https://www.openstreetmap.org/directions?from="
                f"{quote(str(origin.latitude))}%2C{quote(str(origin.longitude))}"
                f"&to={quote(str(destination.point.latitude))}%2C{quote(str(destination.point.longitude))}"
            ),
        }

    def context(self, query: str | None = None) -> dict[str, object]:
        snapshot = self.locate_me()
        payload: dict[str, object] = {"location": snapshot.as_dict()}
        if query is not None and query.strip():
            payload["places"] = [place.as_dict() for place in self.search(query)]
        return payload

    def open_place(self, place: Place) -> dict[str, object]:
        return {
            "place": place.as_dict(),
            "map": {
                "center": place.point.as_dict(),
                "markers": [place.as_dict()],
                "zoom": 12,
                "surface": "gods-eye",
            },
            "navigation_url": (
                "https://www.openstreetmap.org/?mlat="
                f"{place.point.latitude}&mlon={place.point.longitude}#map=12/"
                f"{place.point.latitude}/{place.point.longitude}"
            ),
        }
