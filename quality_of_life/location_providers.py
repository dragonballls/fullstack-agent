"""Provider-neutral, privacy-safe location status contracts for God’s Eye."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Literal, Protocol


ProviderKind = Literal["device", "phone", "family"]
_PROVIDER_KINDS: tuple[ProviderKind, ...] = ("device", "phone", "family")


class LocationStatusProvider(Protocol):
    def status(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ProviderState:
    kind: ProviderKind
    available: bool
    authorized: bool
    live: bool
    source: str
    detail: str

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "available": self.available,
            "authorized": self.authorized,
            "live": self.live,
            "source": self.source,
            "detail": self.detail,
        }


class LocationProviderRegistry:
    """Keeps device, phone, and family location feeds independent and bounded."""

    def __init__(self) -> None:
        self._providers: dict[ProviderKind, Any] = {}

    def register(self, kind: ProviderKind, provider: LocationStatusProvider) -> None:
        if kind not in _PROVIDER_KINDS:
            raise ValueError(f"unsupported location provider kind: {kind}")
        if provider is None:
            raise ValueError("location provider cannot be None")
        self._providers[kind] = provider

    def status(self, kind: ProviderKind) -> ProviderState:
        if kind not in _PROVIDER_KINDS:
            raise ValueError(f"unsupported location provider kind: {kind}")
        provider = self._providers.get(kind)
        if provider is None:
            return ProviderState(
                kind=kind,
                available=False,
                authorized=False,
                live=False,
                source="",
                detail="provider unavailable",
            )
        try:
            raw = provider.status()
            if not isinstance(raw, dict):
                raise TypeError("provider status must be an object")
            return ProviderState(
                kind=kind,
                available=bool(raw.get("available", False)),
                authorized=bool(raw.get("authorized", raw.get("permitted", False))),
                live=bool(raw.get("live", False)),
                source=_safe_text(raw.get("source", ""), 80),
                detail=_safe_text(raw.get("detail", "provider status received"), 240),
            )
        except Exception as exc:
            return ProviderState(
                kind=kind,
                available=False,
                authorized=False,
                live=False,
                source="",
                detail=f"provider unavailable ({type(exc).__name__})",
            )

    def snapshot(self) -> tuple[ProviderState, ...]:
        return tuple(self.status(kind) for kind in _PROVIDER_KINDS)


def _safe_text(value: object, limit: int) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"(?i)(token|api[_-]?key|authorization|password)\s*[=:]\s*(?:Bearer\s+)?([^\s,;]+)", r"\\1=[redacted]", text)
    return text[:limit]
