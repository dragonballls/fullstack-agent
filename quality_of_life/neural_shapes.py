"""Extensible shape descriptors for Neural JARVIS entities."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

BUILTIN_SHAPES = (
    "droplet", "sphere", "crystal", "cube", "torus",
    "capsule", "ring", "star", "orbital", "core", "heart", "gear", "spiral", "pyramid", "wave", "dna", "molecule", "arrow",
)


@dataclass(frozen=True)
class ShapeSpec:
    name: str = "droplet"
    family: str = "primitive"
    parameters: Mapping[str, float] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "family": self.family,
            "parameters": dict(self.parameters) if isinstance(self.parameters, Mapping) else {},
        }


def normalize_shape(value: object) -> ShapeSpec:
    if isinstance(value, Mapping):
        name = str(value.get("name", "droplet")).strip()[:120] or "droplet"
        family = str(value.get("family", "primitive")).strip().lower()[:40] or "primitive"
        raw = value.get("parameters", {})
        params: dict[str, float] = {}
        if isinstance(raw, Mapping):
            for key, raw_value in raw.items():
                try:
                    number = float(raw_value)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(number):
                    params[str(key)[:40]] = max(-1000.0, min(1000.0, number))
        if family not in {"primitive", "parametric", "freeform"}:
            raise ValueError("unsupported shape family")
        return ShapeSpec(name=name, family=family, parameters=params)
    name = str(value or "").strip()[:120] or "droplet"
    return ShapeSpec(name=name, family="primitive" if name.casefold() in BUILTIN_SHAPES else "freeform")
