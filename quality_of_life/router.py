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

    def __init__(self, targets: Iterable[ProviderTarget]) -> None:
        self.targets = tuple(targets)
        if not self.targets:
            raise ValueError("At least one provider target is required")

    def complete(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        errors: list[str] = []
        for target in self.targets:
            key = os.environ.get(target.api_key_env)
            if not key:
                errors.append(f"{target.name}: missing {target.api_key_env}")
                continue
            payload = json.dumps({"model": target.model, "messages": messages}).encode()
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
