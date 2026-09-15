"""Pure map-view state for the God’s Eye surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .gods_eye import GeoPoint, LocationSnapshot, Place


@dataclass(frozen=True)
class MapView:
    center: GeoPoint
    zoom: int
    markers: tuple[Place, ...]
    route: dict[str, object] | None = None
    selected_place_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "surface": "gods-eye",
            "center": self.center.as_dict(),
            "zoom": self.zoom,
            "markers": [place.as_dict() for place in self.markers],
            "route": self.route,
            "selected_place_id": self.selected_place_id,
        }


class GodsEyeMap:
    @staticmethod
    def build_search_view(places: Iterable[Place], selected: Place | None = None) -> MapView:
        markers = tuple(places)
        if not markers and selected is None:
            raise ValueError("at least one place is required")
        anchor = selected or markers[0]
        return MapView(anchor.point, 12, markers or (anchor,), selected_place_id=selected.place_id if selected else None)

    @staticmethod
    def build_location_view(snapshot: LocationSnapshot) -> MapView | None:
        if not snapshot.permitted or snapshot.point is None:
            return None
        return MapView(snapshot.point, 15, ())

    @staticmethod
    def build_route_view(origin: GeoPoint, destination: Place) -> MapView:
        route = {
            "origin": origin.as_dict(),
            "destination": destination.point.as_dict(),
            "navigation_url": (
                "https://www.openstreetmap.org/directions?from="
                f"{origin.latitude}%2C{origin.longitude}"
                f"&to={destination.point.latitude}%2C{destination.point.longitude}"
            ),
        }
        return MapView(origin, 11, (destination,), route=route, selected_place_id=destination.place_id)
