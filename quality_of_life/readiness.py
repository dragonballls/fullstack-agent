"""Safe, non-invasive readiness checks for the Jarvis stack."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping


class CheckStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    status: CheckStatus
    detail: str
    required: bool = False


@dataclass(frozen=True)
class ReadinessReport:
    checks: tuple[ReadinessCheck, ...]

    @property
    def required_status(self) -> CheckStatus:
        if any(check.required and check.status is CheckStatus.FAIL for check in self.checks):
            return CheckStatus.FAIL
        return CheckStatus.PASS

    @property
    def ready(self) -> bool:
        return self.required_status is CheckStatus.PASS


CloudKey = tuple[str, ...]
DEFAULT_CLOUD_KEYS: CloudKey = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
    "COHERE_API_KEY",
    "TOGETHER_API_KEY",
)


def _python_check() -> ReadinessCheck:
    supported = sys.version_info >= (3, 11)
    detail = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return ReadinessCheck("Python runtime", CheckStatus.PASS if supported else CheckStatus.FAIL, detail, True)


def _git_check(which: Callable[[str], str | None]) -> ReadinessCheck:
    path = which("git")
    return ReadinessCheck(
        "Git", CheckStatus.PASS if path else CheckStatus.FAIL,
        "available" if path else "git executable not found",
        True,
    )


def _cloud_check(env: Mapping[str, str], cloud_keys: CloudKey) -> ReadinessCheck:
    configured = next((name for name in cloud_keys if env.get(name)), None)
    if configured:
        return ReadinessCheck("Cloud LLM", CheckStatus.PASS, f"configured via {configured}", True)
    names = ", ".join(cloud_keys)
    return ReadinessCheck("Cloud LLM", CheckStatus.FAIL, f"configure at least one supported key: {names}", True)


def _optional_import_check(
    name: str,
    display: str,
    importable: Callable[[str], bool],
    detail_when_missing: str,
) -> ReadinessCheck:
    available = importable(name)
    return ReadinessCheck(display, CheckStatus.PASS if available else CheckStatus.WARNING, "available" if available else detail_when_missing)


def check_readiness(
    *,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    importable: Callable[[str], bool] | None = None,
    cloud_keys: CloudKey = DEFAULT_CLOUD_KEYS,
) -> ReadinessReport:
    """Return a non-invasive readiness report without revealing secret values."""
    environment = os.environ if env is None else env
    if importable is None:
        importable = lambda module: importlib.util.find_spec(module) is not None

    checks = [
        _python_check(),
        _git_check(which),
        _cloud_check(environment, cloud_keys),
        _optional_import_check("webview", "God's Eye desktop surface", importable, "pywebview is not installed"),
        _optional_import_check("playwright", "Browser automation", importable, "Playwright is not installed"),
    ]

    elevenlabs = bool(environment.get("ELEVENLABS_API_KEY"))
    checks.append(
        ReadinessCheck(
            "ElevenLabs voice",
            CheckStatus.PASS if elevenlabs else CheckStatus.WARNING,
            "API key configured" if elevenlabs else "ELEVENLABS_API_KEY is not configured; use the built-in voice fallback",
        )
    )

    self_coding_cli = any(which(name) for name in ("claude", "codex", "gemini"))
    checks.append(
        ReadinessCheck(
            "Cloud coding CLI",
            CheckStatus.PASS if self_coding_cli else CheckStatus.WARNING,
            "a supported coding CLI is available" if self_coding_cli else "no supported coding CLI found; self-coding remains unavailable until one is installed/authenticated",
        )
    )

    return ReadinessReport(tuple(checks))


def format_report(report: ReadinessReport) -> str:
    """Format a report using names/statuses only; never include secret values."""
    lines = ["Jarvis readiness", "=" * 15]
    for check in report.checks:
        required = " required" if check.required else " optional"
        lines.append(f"[{check.status.value}] {check.name} ({required}) - {check.detail}")
    lines.append("")
    lines.append("READY" if report.ready else "NOT READY")
    return "\n".join(lines)
