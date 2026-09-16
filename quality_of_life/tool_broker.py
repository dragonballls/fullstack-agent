"""Extensible, policy-aware broker for Jarvis tool adapters."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Any, Protocol

from .capabilities import OperationRisk, OperationSpec, operation
from .permissions import Capability, CapabilityPolicy


UNIVERSAL_OPERATION_SPECS: tuple[OperationSpec, ...] = (
    OperationSpec("web.fetch", Capability.SYSTEM_DIAGNOSTICS, OperationRisk.READ, "Fetch an allowlisted HTTPS web resource"),
    OperationSpec("web.search", Capability.SYSTEM_DIAGNOSTICS, OperationRisk.READ, "Search through the configured web search provider"),
    OperationSpec("api.request.read", Capability.ACCOUNT_READ, OperationRisk.READ, "Read from a configured JSON API endpoint"),
    OperationSpec("api.request.write", Capability.ACCOUNT_WRITE, OperationRisk.EXTERNAL, "Write to a configured JSON API endpoint"),
    OperationSpec("tools.list", Capability.CLOUD_ROUTING, OperationRisk.READ, "List universal tool adapters"),
    OperationSpec("tools.describe", Capability.CLOUD_ROUTING, OperationRisk.READ, "Describe a universal tool adapter"),
    OperationSpec("tools.invoke", Capability.CLOUD_ROUTING, OperationRisk.EXTERNAL, "Invoke a registered universal tool operation"),
)
_UNIVERSAL_OPERATION_MAP = {spec.name: spec for spec in UNIVERSAL_OPERATION_SPECS}


@dataclass(frozen=True)
class ToolManifest:
    name: str
    description: str
    operations: tuple[str, ...]


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    operation: str
    data: Any | None = None
    error: str | None = None
    truncated: bool = False


class ToolAdapter(Protocol):
    def manifest(self) -> ToolManifest: ...
    def invoke(self, operation: str, arguments: dict[str, object]) -> Any: ...


class UniversalToolBroker:
    """Discover and invoke adapters through the existing capability policy."""

    def __init__(self, policy: CapabilityPolicy | None = None, *, timeout_seconds: float = 20.0, max_result_chars: int = 50_000) -> None:
        self.policy = policy or CapabilityPolicy()
        self.timeout_seconds = max(0.1, timeout_seconds)
        self.max_result_chars = max(1_000, max_result_chars)
        self._adapters: dict[str, ToolAdapter] = {}
        self._operation_to_tool: dict[str, str] = {}

    def register(self, adapter: ToolAdapter) -> None:
        manifest = adapter.manifest()
        if not manifest.name.strip():
            raise ValueError("tool name must not be empty")
        if manifest.name in self._adapters:
            raise ValueError(f"tool already registered: {manifest.name}")
        for op_name in manifest.operations:
            self._resolve_spec(op_name)
            if op_name in self._operation_to_tool:
                raise ValueError(f"operation already registered: {op_name}")
        self._adapters[manifest.name] = adapter
        for op_name in manifest.operations:
            self._operation_to_tool[op_name] = manifest.name

    def list_manifests(self) -> tuple[ToolManifest, ...]:
        return tuple(sorted((adapter.manifest() for adapter in self._adapters.values()), key=lambda item: item.name))

    def describe(self, name: str) -> ToolManifest:
        try:
            return self._adapters[name].manifest()
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    def invoke(self, operation_name: str, arguments: dict[str, object], *, confirmed: bool = False) -> ToolResult:
        try:
            spec = self._resolve_spec(operation_name)
        except KeyError as exc:
            return ToolResult(False, operation_name, error=str(exc))
        try:
            self.policy.check(spec.capability)
        except PermissionError as exc:
            return ToolResult(False, operation_name, error=str(exc))
        if spec.risk is not OperationRisk.READ and not confirmed and self.policy.needs_confirmation(spec.capability):
            return ToolResult(False, operation_name, error="confirmation required before this tool operation")
        tool_name = self._operation_to_tool.get(operation_name)
        if tool_name is None:
            return ToolResult(False, operation_name, error="no adapter is registered for this operation")
        adapter = self._adapters[tool_name]
        try:
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="jarvis-tool") as executor:
                future = executor.submit(adapter.invoke, operation_name, dict(arguments))
                raw = future.result(timeout=self.timeout_seconds)
        except FutureTimeout:
            return ToolResult(False, operation_name, error="tool operation timed out")
        except Exception as exc:
            return ToolResult(False, operation_name, error=self._safe_error(exc))
        data, truncated = self._bound_result(raw)
        return ToolResult(True, operation_name, data=data, truncated=truncated)

    @staticmethod
    def _resolve_spec(operation_name: str) -> OperationSpec:
        try:
            return operation(operation_name)
        except KeyError:
            try:
                return _UNIVERSAL_OPERATION_MAP[operation_name]
            except KeyError as exc:
                raise KeyError(f"unknown capability operation: {operation_name}") from exc

    def _bound_result(self, value: Any) -> tuple[Any, bool]:
        if isinstance(value, str):
            if len(value) <= self.max_result_chars:
                return value, False
            return value[: self.max_result_chars] + "\n[truncated]", True
        if isinstance(value, dict):
            result = dict(value)
            text = str(result.get("body", result.get("text", "")))
            if len(text) > self.max_result_chars:
                key = "body" if "body" in result else "text"
                result[key] = text[: self.max_result_chars] + "\n[truncated]"
                result["truncated"] = True
                return result, True
            return result, False
        return value, False

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        message = str(exc).replace("\r", " ").replace("\n", " ").strip()
        if len(message) > 1_000:
            message = message[:1_000] + "..."
        return message or exc.__class__.__name__
