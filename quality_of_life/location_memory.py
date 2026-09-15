"""Persistent, policy-neutral storage for user-named locations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .gods_eye import GeoPoint, LocationSnapshot


@dataclass(frozen=True)
class SavedLocation:
    name: str
    point: GeoPoint
    address: str | None = None
    accuracy_m: float | None = None
    source: str = "user"

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "point": self.point.as_dict(),
            "address": self.address,
            "accuracy_m": self.accuracy_m,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "SavedLocation":
        point_data = value["point"]
        if not isinstance(point_data, dict):
            raise ValueError("saved location point must be an object")
        return cls(
            name=str(value["name"]),
            point=GeoPoint(float(point_data["latitude"]), float(point_data["longitude"])),
            address=str(value["address"]) if value.get("address") is not None else None,
            accuracy_m=float(value["accuracy_m"]) if value.get("accuracy_m") is not None else None,
            source=str(value.get("source", "user")),
        )


class SavedLocationStore:
    """Small JSON store; callers remain responsible for capability checks/confirmation."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else Path.home() / ".jarvis" / "saved_locations.json"

    @staticmethod
    def _key(name: str) -> str:
        normalized = " ".join(name.casefold().split())
        if not normalized:
            raise ValueError("location name cannot be empty")
        return normalized

    def _read(self) -> dict[str, SavedLocation]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("saved locations file must contain an object")
        return {key: SavedLocation.from_dict(value) for key, value in payload.items() if isinstance(value, dict)}

    def _write(self, locations: dict[str, SavedLocation]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: value.as_dict() for key, value in sorted(locations.items())}
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)

    def save(
        self,
        name: str,
        point: GeoPoint,
        *,
        address: str | None = None,
        accuracy_m: float | None = None,
        source: str = "user",
    ) -> SavedLocation:
        location = SavedLocation(
            name=" ".join(name.split()),
            point=point,
            address=address,
            accuracy_m=accuracy_m,
            source=source,
        )
        locations = self._read()
        locations[self._key(location.name)] = location
        self._write(locations)
        return location

    def save_current(self, name: str, snapshot: LocationSnapshot, *, address: str | None = None) -> SavedLocation:
        if not snapshot.permitted or snapshot.point is None:
            raise PermissionError("current location is unavailable or permission was not granted")
        return self.save(name, snapshot.point, address=address, accuracy_m=snapshot.accuracy_m, source=snapshot.source)

    def get(self, name: str) -> SavedLocation | None:
        return self._read().get(self._key(name))

    def list(self) -> tuple[SavedLocation, ...]:
        return tuple(self._read().values())

    def delete(self, name: str) -> bool:
        locations = self._read()
        key = self._key(name)
        if key not in locations:
            return False
        del locations[key]
        self._write(locations)
        return True
