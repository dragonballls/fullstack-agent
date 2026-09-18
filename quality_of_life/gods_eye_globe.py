"""Guarded 3D Earth locator payload for God's Eye."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .permissions import Capability


@dataclass(frozen=True)
class GlobeLocator:
    id: str
    label: str
    latitude: float
    longitude: float
    kind: str
    authorized: bool
    accuracy_m: float | None = None
    source: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "kind": self.kind,
            "authorized": self.authorized,
            "accuracy_m": self.accuracy_m,
            "source": self.source,
        }


def _point(raw: object) -> tuple[float, float] | None:
    if not isinstance(raw, dict):
        return None
    point = raw.get("point")
    if not isinstance(point, dict):
        return None
    try:
        lat, lon = float(point["latitude"]), float(point["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    return (lat, lon) if -90 <= lat <= 90 and -180 <= lon <= 180 else None


def globe_payload(runtime: Any) -> dict[str, object]:
    current = runtime.dispatch(Capability.LOCATION_READ, "locations.current")
    current = current.as_dict() if hasattr(current, "as_dict") else current if isinstance(current, dict) else {}
    locators: list[GlobeLocator] = []
    point = _point(current)
    if bool(current.get("permitted", False)) and point is not None:
        locators.append(GlobeLocator(
            "current", "Current location", point[0], point[1], "current", True,
            current.get("accuracy_m"), str(current.get("source", ""))[:80],
        ))
    try:
        eye = runtime._tool("gods_eye")
    except Exception:
        eye = None
    if eye is not None:
        for kind in ("device", "phone", "family"):
            for index, item in enumerate(eye.provider_locations(kind)):
                point = _point(item)
                if point is None or not bool(item.get("authorized", True)):
                    continue
                label = str(item.get("label", item.get("name", kind.title())))[:120]
                locators.append(GlobeLocator(
                    f"{kind}:{index}:{label.casefold().replace(' ', '-')[:50]}",
                    label, point[0], point[1], kind, True,
                    item.get("accuracy_m"), str(item.get("source", kind))[:80],
                ))
    saved = runtime.dispatch(Capability.LOCATION_READ, "locations.list")
    for item in saved or ():
        raw = item.as_dict() if hasattr(item, "as_dict") else item if isinstance(item, dict) else {}
        point = _point(raw)
        if point is None:
            continue
        label = str(raw.get("name", "Saved location"))[:120]
        locators.append(GlobeLocator(
            "saved:" + label.casefold().replace(" ", "-")[:90],
            label, point[0], point[1], "saved", True,
            raw.get("accuracy_m"), str(raw.get("source", ""))[:80],
        ))
    return {
        "schema_version": 1,
        "authorized_current": bool(current.get("permitted", False) and _point(current) is not None),
        "locators": [item.as_dict() for item in locators],
    }
