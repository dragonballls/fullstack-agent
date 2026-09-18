"""Cloud-model routing with deterministic failover, latency awareness, and bounded parallel calls."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable, Sequence

from .omniroute import OmniRouteConnection
from .orchestration import RequestProfile


def _is_loopback_hostname(hostname: str | None) -> bool:
    """Return True when a hostname resolves syntactically to a loopback address."""
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
    """Describe one cloud routing target."""

    name: str
    base_url: str
    api_key_env: str
    model: str
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
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
        """Return whether the target is local/loopback and therefore may use HTTP."""
        return _is_loopback_hostname(urllib.parse.urlparse(self.base_url).hostname)


@dataclass(frozen=True)
class ProviderResult:
    """Represent one provider attempt."""

    ok: bool
    text: str | None
    target_name: str
    latency_ms: int
    error: str | None = None


class CloudModelRouter:
    """Route cloud-only model requests with health-aware ordering and bounded concurrency."""

    OMNIROUTE_BASE_URL = "http://127.0.0.1:20128/v1"
    OMNIROUTE_API_KEY_ENV = "OMNIROUTE_API_KEY"
    OMNIROUTE_MODEL = "auto"
    PROFILE_ENV_NAMES = {
        RequestProfile.FAST: "JARVIS_OMNIROUTE_FAST_MODEL",
        RequestProfile.SMART: "JARVIS_OMNIROUTE_SMART_MODEL",
        RequestProfile.CODING: "JARVIS_OMNIROUTE_CODING_MODEL",
        RequestProfile.VISION: "JARVIS_OMNIROUTE_VISION_MODEL",
        RequestProfile.MAINTENANCE: "JARVIS_OMNIROUTE_MAINTENANCE_MODEL",
    }
    PROFILE_DEFAULTS = {
        RequestProfile.FAST: "auto/fast",
        RequestProfile.SMART: "auto/smart",
        RequestProfile.CODING: "auto/coding",
        RequestProfile.VISION: "auto/smart",
        RequestProfile.MAINTENANCE: "auto/smart",
    }
    _failure_lock = threading.Lock()
    _failure_cooldowns: dict[tuple[str, str], float] = {}
    _health_lock = threading.Lock()
    _latency_ewma_ms: dict[tuple[str, str, str], float] = {}
    _latency_samples: dict[tuple[str, str, str], int] = {}
    _EWMA_ALPHA = 0.25
    _omniroute_lock = threading.Lock()
    _omniroute_connections: dict[tuple[str, str], OmniRouteConnection] = {}

    def __init__(self, targets: Iterable[ProviderTarget]) -> None:
        self.targets = tuple(targets)
        if not self.targets:
            raise ValueError("At least one provider target is required")

    @classmethod
    def omniroute_base_url(cls) -> str:
        """Return the configured OmniRoute base URL."""
        return os.environ.get("JARVIS_OMNIROUTE_BASE_URL", cls.OMNIROUTE_BASE_URL)

    @classmethod
    def omniroute_api_key_env(cls) -> str:
        """Return the environment variable containing the OmniRoute key."""
        return os.environ.get("JARVIS_OMNIROUTE_API_KEY_ENV", cls.OMNIROUTE_API_KEY_ENV)

    @classmethod
    def omniroute_model(cls) -> str:
        """Return the configured default OmniRoute model."""
        return os.environ.get("JARVIS_OMNIROUTE_MODEL", cls.OMNIROUTE_MODEL)

    @classmethod
    def profile_model(cls, profile: RequestProfile | str) -> str:
        """Resolve the model alias for a request profile."""
        if isinstance(profile, str):
            profile = RequestProfile(profile)
        env_name = cls.PROFILE_ENV_NAMES[profile]
        return os.environ.get(env_name, cls.PROFILE_DEFAULTS[profile])

    @classmethod
    def omniroute_target(cls, model: str | None = None) -> ProviderTarget:
        """Build the default OmniRoute target."""
        return ProviderTarget("omniroute", cls.omniroute_base_url(), cls.omniroute_api_key_env(), model or cls.omniroute_model())

    @classmethod
    def _ensure_omniroute(cls, target: ProviderTarget) -> bool:
        """Lazily connect to local OmniRoute and start it when configured."""
        if target.name.casefold() != "omniroute" or not target.is_loopback:
            return True
        key = (target.base_url.rstrip("/"), target.api_key_env)
        with cls._omniroute_lock:
            connection = cls._omniroute_connections.get(key)
            if connection is None:
                connection = OmniRouteConnection(target.base_url, target.api_key_env, timeout_seconds=min(2.0, target.timeout_seconds))
                cls._omniroute_connections[key] = connection
        return connection.ensure_ready()

    @staticmethod
    def prepare_messages(messages: list[dict[str, str]], system_prompt: str | None = None) -> list[dict[str, str]]:
        """Return a copy of messages with an optional system prompt merged in."""
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

    @classmethod
    def _cooldown_seconds(cls) -> float:
        """Return the configured provider-failure cooldown duration."""
        try:
            return max(0.0, float(os.environ.get("JARVIS_OMNIROUTE_FAILURE_COOLDOWN", "10")))
        except ValueError:
            return 10.0

    @classmethod
    def _cooldown_active(cls, target: ProviderTarget) -> bool:
        """Return whether a target is currently cooling down."""
        key = (target.base_url, target.model)
        with cls._failure_lock:
            return cls._failure_cooldowns.get(key, 0.0) > time.monotonic()

    @classmethod
    def _record_failure(cls, target: ProviderTarget) -> None:
        """Record a failed target so repeated failures are temporarily avoided."""
        cooldown = cls._cooldown_seconds()
        if cooldown <= 0:
            return
        with cls._failure_lock:
            cls._failure_cooldowns[(target.base_url, target.model)] = time.monotonic() + cooldown

    @classmethod
    def _clear_failure(cls, target: ProviderTarget) -> None:
        """Clear a target's failure cooldown after a successful call."""
        with cls._failure_lock:
            cls._failure_cooldowns.pop((target.base_url, target.model), None)

    @classmethod
    def _health_key(cls, target: ProviderTarget) -> tuple[str, str, str]:
        """Return a stable latency key scoped to provider, endpoint, and model."""
        return (target.name, target.base_url.rstrip("/"), target.model)

    @classmethod
    def _record_success(cls, target: ProviderTarget, latency_ms: int) -> None:
        """Update the exponentially weighted latency estimate for a target."""
        key = cls._health_key(target)
        latency = max(0, latency_ms)
        with cls._health_lock:
            previous = cls._latency_ewma_ms.get(key)
            cls._latency_ewma_ms[key] = float(latency) if previous is None else (cls._EWMA_ALPHA * latency) + ((1.0 - cls._EWMA_ALPHA) * previous)
            cls._latency_samples[key] = cls._latency_samples.get(key, 0) + 1

    @classmethod
    def provider_latency_ms(cls, target_name: str, profile: RequestProfile | str = RequestProfile.FAST) -> int:
        """Return the learned latency for a named provider/profile, or zero if unknown."""
        selected = RequestProfile(profile)
        model = cls.profile_model(selected)
        with cls._health_lock:
            values = [latency for (provider_name, _base_url, target_model), latency in cls._latency_ewma_ms.items() if provider_name == target_name and target_model == model]
        return int(round(min(values))) if values else 0

    @classmethod
    def _ordered_targets(cls, targets: Sequence[ProviderTarget]) -> tuple[ProviderTarget, ...]:
        """Order warmed targets by learned latency while preserving unseen configuration order."""
        indexed = list(enumerate(targets))
        with cls._health_lock:
            latency = dict(cls._latency_ewma_ms)
            samples = dict(cls._latency_samples)
        indexed.sort(
            key=lambda item: (
                0 if samples.get(cls._health_key(item[1]), 0) else 1,
                latency.get(cls._health_key(item[1]), float("inf")),
                item[0],
            )
        )
        return tuple(target for _, target in indexed)

    def try_target(self, target: ProviderTarget, messages: list[dict[str, str]]) -> ProviderResult:
        """Attempt one provider call and record its latency/health outcome."""
        started = time.monotonic()
        if self._cooldown_active(target):
            return ProviderResult(False, None, target.name, 0, "target temporarily cooling down after a recent failure")
        if not self._ensure_omniroute(target):
            return ProviderResult(False, None, target.name, int((time.monotonic() - started) * 1000), "omniroute is not reachable and could not be started")
        key = os.environ.get(target.api_key_env)
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        elif not target.is_loopback:
            return ProviderResult(False, None, target.name, 0, f"{target.name}: missing {target.api_key_env}")
        payload = json.dumps({"model": target.model, "messages": self.prepare_messages(messages, os.environ.get("JARVIS_SYSTEM_PROMPT"))}).encode()
        request = urllib.request.Request(target.base_url.rstrip("/") + "/chat/completions", data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=target.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("provider returned an empty response")
            latency_ms = int((time.monotonic() - started) * 1000)
            self._clear_failure(target)
            self._record_success(target, latency_ms)
            return ProviderResult(True, content, target.name, latency_ms)
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
            latency_ms = int((time.monotonic() - started) * 1000)
            self._record_failure(target)
            return ProviderResult(False, None, target.name, latency_ms, f"{target.name}: provider request failed ({exc})")

    def complete(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        """Complete a request through the fastest known healthy target."""
        errors: list[str] = []
        for target in self._ordered_targets(self.targets):
            result = self.try_target(target, messages)
            if result.ok and result.text is not None:
                return result.text, result.target_name
            if result.error:
                errors.append(result.error)
        raise RuntimeError("All configured cloud targets failed: " + " | ".join(errors))

    def complete_profiled(self, messages: list[dict[str, str]], profile: RequestProfile | str) -> tuple[str, str]:
        """Complete a profiled request using latency-aware target ordering."""
        selected = RequestProfile(profile)
        targets = tuple(ProviderTarget(target.name, target.base_url, target.api_key_env, self.profile_model(selected), target.timeout_seconds) for target in self.targets)
        errors: list[str] = []
        for target in self._ordered_targets(targets):
            result = self.try_target(target, messages)
            if result.ok and result.text is not None:
                return result.text, result.target_name
            if result.error:
                errors.append(result.error)
        raise RuntimeError("All configured cloud targets failed: " + " | ".join(errors))

    def complete_many(
        self,
        requests: Sequence[tuple[list[dict[str, str]], RequestProfile | str]],
        max_parallel: int | None = None,
    ) -> tuple[ProviderResult, ...]:
        """Run independent model requests concurrently with a bounded worker pool."""
        if not requests:
            return ()
        if max_parallel is None:
            try:
                max_parallel = int(os.environ.get("JARVIS_OMNIROUTE_MAX_PARALLEL", "4"))
            except ValueError:
                max_parallel = 4
        worker_count = max(1, min(max_parallel, len(requests), 8))

        def run_one(item: tuple[list[dict[str, str]], RequestProfile | str]) -> ProviderResult:
            messages, profile = item
            selected = RequestProfile(profile)
            targets = tuple(ProviderTarget(target.name, target.base_url, target.api_key_env, self.profile_model(selected), target.timeout_seconds) for target in self.targets)
            failures: list[str] = []
            started = time.monotonic()
            for target in self._ordered_targets(targets):
                result = self.try_target(target, messages)
                if result.ok and result.text is not None:
                    return result
                if result.error:
                    failures.append(result.error)
            return ProviderResult(False, None, targets[0].name, int((time.monotonic() - started) * 1000), " | ".join(failures))

        results: list[ProviderResult | None] = [None] * len(requests)
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="jarvis-ai") as executor:
            futures = {executor.submit(run_one, item): index for index, item in enumerate(requests)}
            for future in as_completed(futures):
                results[futures[future]] = future.result()
        return tuple(result for result in results if result is not None)
