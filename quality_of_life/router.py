"""Minimal cloud-model router with deterministic failover."""

from __future__ import annotations

import ipaddress
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable


def _is_loopback_hostname(hostname: str | None) -> bool:
    """Return whether a hostname identifies the local loopback interface."""
    if not hostname:
        return False
    normalized = hostname.strip().lower().rstrip(".")
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True)
class ProviderTarget:
    """Describe one OpenAI-compatible endpoint and its optional credential."""

    name: str
    base_url: str
    api_key_env: str
    model: str
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        """Validate endpoint, credential-variable, model, and timeout configuration."""
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("base_url must be an absolute HTTP(S) URL without embedded credentials")
        if parsed.scheme == "http" and not _is_loopback_hostname(parsed.hostname):
            raise ValueError("HTTPS is required for non-loopback cloud targets")
        if not self.name.strip():
            raise ValueError("name must be non-empty")
        if not self.api_key_env.strip():
            raise ValueError("api_key_env must be non-empty")
        if not self.model.strip():
            raise ValueError("model must be non-empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    @property
    def is_loopback(self) -> bool:
        """Return whether this endpoint targets localhost or another loopback address."""
        return _is_loopback_hostname(urllib.parse.urlparse(self.base_url).hostname)


class CloudModelRouter:
    """Try configured OpenAI-compatible cloud targets in priority order."""

    OMNIROUTE_BASE_URL = "http://127.0.0.1:20128/v1"
    OMNIROUTE_API_KEY_ENV = "OMNIROUTE_API_KEY"
    OMNIROUTE_MODEL = "auto"

    def __init__(self, targets: Iterable[ProviderTarget]) -> None:
        """Create a router from one or more validated provider targets."""
        self.targets = tuple(targets)
        if not self.targets:
            raise ValueError("At least one provider target is required")

    @classmethod
    def omniroute_base_url(cls) -> str:
        """Return the configured OmniRoute OpenAI-compatible base URL."""
        return os.environ.get("JARVIS_OMNIROUTE_BASE_URL", cls.OMNIROUTE_BASE_URL)

    @classmethod
    def omniroute_api_key_env(cls) -> str:
        """Return the environment variable used for an OmniRoute credential."""
        return os.environ.get("JARVIS_OMNIROUTE_API_KEY_ENV", cls.OMNIROUTE_API_KEY_ENV)

    @classmethod
    def omniroute_model(cls) -> str:
        """Return the model selector sent to OmniRoute."""
        return os.environ.get("JARVIS_OMNIROUTE_MODEL", cls.OMNIROUTE_MODEL)

    @classmethod
    def omniroute_target(cls) -> ProviderTarget:
        """Build a validated provider target for the existing local OmniRoute gateway."""
        return ProviderTarget(
            "omniroute",
            cls.omniroute_base_url(),
            cls.omniroute_api_key_env(),
            cls.omniroute_model(),
        )

    @staticmethod
    def prepare_messages(messages: list[dict[str, str]], system_prompt: str | None = None) -> list[dict[str, str]]:
        """Return a fresh message list with an optional global Jarvis prompt."""
        prepared = [dict(message) for message in messages]
        prompt = (system_prompt or "").strip()
        if not prompt:
            return prepared
        for message in prepared:
            if message.get("role") == "system":
                existing = str(message.get("content", "")).strip()
                message["content"] = f"{existing}\n\n{prompt}" if existing else prompt
                return prepared
        prepared.insert(0, {"role": "system", "content": prompt})
        return prepared

    def complete(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        """Send a chat completion request and return its text plus the successful target name."""
        errors: list[str] = []
        prepared_messages = self.prepare_messages(messages, os.environ.get("JARVIS_SYSTEM_PROMPT"))
        for target in self.targets:
            key = os.environ.get(target.api_key_env)
            headers = {"Content-Type": "application/json"}
            if key:
                headers["Authorization"] = f"Bearer {key}"
            elif not target.is_loopback:
                errors.append(f"{target.name}: missing {target.api_key_env}")
                continue
            payload = json.dumps({"model": target.model, "messages": prepared_messages}).encode()
            request = urllib.request.Request(
                target.base_url.rstrip("/") + "/chat/completions",
                data=payload,
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=target.timeout_seconds) as response:
                    data = json.loads(response.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content:
                    raise ValueError("provider returned an empty response")
                return content, target.name
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
                errors.append(f"{target.name}: provider request failed ({exc})")
        raise RuntimeError("All configured cloud targets failed: " + " | ".join(errors))
