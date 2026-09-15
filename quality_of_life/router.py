"""Minimal cloud-model router with deterministic failover."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ProviderTarget:
    name: str
    base_url: str
    api_key_env: str
    model: str
    timeout_seconds: int = 60


class CloudModelRouter:
    """Try configured OpenAI-compatible cloud targets in priority order."""

    OMNIROUTE_BASE_URL = "http://127.0.0.1:20128/v1"
    OMNIROUTE_API_KEY_ENV = "OMNIROUTE_API_KEY"
    OMNIROUTE_MODEL = "auto"

    def __init__(self, targets: Iterable[ProviderTarget]) -> None:
        self.targets = tuple(targets)
        if not self.targets:
            raise ValueError("At least one provider target is required")

    @classmethod
    def omniroute_base_url(cls) -> str:
        return os.environ.get("JARVIS_OMNIROUTE_BASE_URL", cls.OMNIROUTE_BASE_URL)

    @classmethod
    def omniroute_api_key_env(cls) -> str:
        return os.environ.get("JARVIS_OMNIROUTE_API_KEY_ENV", cls.OMNIROUTE_API_KEY_ENV)

    @classmethod
    def omniroute_model(cls) -> str:
        return os.environ.get("JARVIS_OMNIROUTE_MODEL", cls.OMNIROUTE_MODEL)

    @classmethod
    def omniroute_target(cls) -> ProviderTarget:
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
        errors: list[str] = []
        prepared_messages = self.prepare_messages(messages, os.environ.get("JARVIS_SYSTEM_PROMPT"))
        for target in self.targets:
            key = os.environ.get(target.api_key_env)
            if not key:
                errors.append(f"{target.name}: missing {target.api_key_env}")
                continue
            payload = json.dumps({"model": target.model, "messages": prepared_messages}).encode()
            request = urllib.request.Request(
                target.base_url.rstrip("/") + "/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
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
                errors.append(f"{target.name}: {exc}")
        raise RuntimeError("All configured cloud targets failed: " + " | ".join(errors))
