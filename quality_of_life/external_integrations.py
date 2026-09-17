"""Optional bridges for complementary external agent projects.

The bridges are intentionally dependency-free and inactive unless explicitly configured.
They let Jarvis use compatible capabilities without replacing the core runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ExternalSkillSpec:
    name: str
    purpose: str
    repository: str
    kind: str
    command: str | None = None
    environment: str | None = None


EXTERNAL_SKILLS: tuple[ExternalSkillSpec, ...] = (
    ExternalSkillSpec("archify", "Verified architecture and lifecycle diagrams", "https://github.com/dragonballls/archify", "cli-skill", "npx skills use tt-a1i/archify@archify --agent codex"),
    ExternalSkillSpec("go-modern-guidelines", "Modern Go guidance", "https://github.com/dragonballls/go-modern-guidelines", "guidance-skill"),
    ExternalSkillSpec("openclaude", "Optional multi-provider coding-agent harness", "https://github.com/dragonballls/openclaude", "agent-harness", "openclaude"),
    ExternalSkillSpec("scientific-agent-skills", "Optional scientific research skill library", "https://github.com/dragonballls/scientific-agent-skills", "skill-library"),
    ExternalSkillSpec("omarchy", "Linux desktop reference only", "https://github.com/dragonballls/omarchy", "platform-reference"),
    ExternalSkillSpec("hindsight", "Optional long-term agent memory backend", "https://github.com/dragonballls/hindsight", "memory-backend", environment="JARVIS_HINDSIGHT_URL"),
    ExternalSkillSpec("radiant", "Optional Mac coding-agent reference", "https://github.com/dragonballls/radiant", "platform-reference"),
)


class ExternalSkillRegistry:
    """Read-only catalog plus opt-in availability detection."""

    def __init__(self, specs: tuple[ExternalSkillSpec, ...] = EXTERNAL_SKILLS) -> None:
        self._specs = {spec.name: spec for spec in specs}

    def list(self) -> tuple[ExternalSkillSpec, ...]:
        return tuple(self._specs[name] for name in sorted(self._specs))

    def get(self, name: str) -> ExternalSkillSpec:
        normalized = " ".join(name.casefold().split())
        try:
            return self._specs[normalized]
        except KeyError as exc:
            raise KeyError(f"unknown external skill: {name}") from exc

    def available(self, name: str) -> bool:
        spec = self.get(name)
        if spec.environment:
            return bool(os.environ.get(spec.environment, "").strip())
        if spec.command:
            return shutil.which(spec.command.split()[0]) is not None
        return False


class HindsightMemoryBridge:
    """Minimal HTTP bridge for an explicitly configured Hindsight service."""

    def __init__(self, base_url: str | None = None, timeout: float = 8.0) -> None:
        self.base_url = (base_url or os.environ.get("JARVIS_HINDSIGHT_URL", "")).strip().rstrip("/")
        self.timeout = float(timeout)

    @property
    def configured(self) -> bool:
        return self.base_url.startswith(("http://", "https://"))

    def _request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("Hindsight memory backend is not configured")
        request = Request(f"{self.base_url}{path}", data=json.dumps(payload, ensure_ascii=True).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"Hindsight request failed: {type(exc).__name__}") from exc
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Hindsight returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise RuntimeError("Hindsight returned a non-object JSON response")
        return value

    def retain(self, bank_id: str, content: str) -> dict[str, Any]:
        return self._request("/v1/retain", {"bank_id": bank_id, "content": content})

    def recall(self, bank_id: str, query: str, limit: int = 8) -> dict[str, Any]:
        return self._request("/v1/recall", {"bank_id": bank_id, "query": query, "limit": min(max(int(limit), 1), 50)})


class OptionalAgentLauncher:
    """Launch an explicitly installed external coding harness without shell strings."""

    def __init__(self, executable: str = "openclaude", timeout: float = 3.0) -> None:
        self.executable = executable
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return shutil.which(self.executable) is not None

    def version(self) -> str:
        if not self.available:
            raise RuntimeError("OpenClaude is not installed")
        try:
            completed = subprocess.run([self.executable, "--version"], check=True, capture_output=True, text=True, timeout=self.timeout, shell=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(f"OpenClaude version check failed: {type(exc).__name__}") from exc
        return completed.stdout.strip() or completed.stderr.strip()


def external_skill_status() -> list[dict[str, Any]]:
    registry = ExternalSkillRegistry()
    launcher = OptionalAgentLauncher()
    result: list[dict[str, Any]] = []
    for spec in registry.list():
        available = registry.available(spec.name)
        item: dict[str, Any] = {"name": spec.name, "kind": spec.kind, "available": available, "repository": spec.repository}
        if spec.name == "openclaude" and available:
            try:
                item["version"] = launcher.version()
            except RuntimeError:
                item["version"] = None
        result.append(item)
    return result


def load_skill_text(path: str | Path, max_bytes: int = 200_000) -> str:
    data = Path(path).read_bytes()
    if len(data) > max_bytes:
        raise ValueError("external skill file exceeds the configured size limit")
    return data.decode("utf-8")
