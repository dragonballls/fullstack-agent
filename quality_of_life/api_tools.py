"""Allowlisted JSON REST adapter for the universal tool broker."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .tool_broker import ToolManifest


@dataclass(frozen=True)
class ApiEndpoint:
    name: str
    base_url: str
    key_env: str | None = None
    allowed_paths: tuple[str, ...] = ()

    def validate(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError(f"endpoint {self.name!r} must use credential-free HTTPS")


class ApiToolAdapter:
    def __init__(self, endpoints: tuple[ApiEndpoint, ...], *, timeout_seconds: float = 10.0, max_bytes: int = 1_000_000) -> None:
        self.endpoints = {endpoint.name: endpoint for endpoint in endpoints}
        for endpoint in self.endpoints.values():
            endpoint.validate()
        self.timeout_seconds = max(0.5, timeout_seconds)
        self.max_bytes = max(1_024, max_bytes)

    @classmethod
    def from_environment(cls) -> "ApiToolAdapter":
        raw = os.environ.get("JARVIS_API_ENDPOINTS_JSON", "[]")
        try:
            items = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("JARVIS_API_ENDPOINTS_JSON must contain valid JSON") from exc
        if not isinstance(items, list):
            raise ValueError("JARVIS_API_ENDPOINTS_JSON must be a JSON array")
        endpoints: list[ApiEndpoint] = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("each API endpoint configuration must be an object")
            endpoints.append(ApiEndpoint(str(item["name"]), str(item["base_url"]), str(item["key_env"]) if item.get("key_env") else None, tuple(str(path) for path in item.get("allowed_paths", ()))))
        return cls(tuple(endpoints))

    def manifest(self) -> ToolManifest:
        return ToolManifest("api", "Allowlisted JSON REST APIs with secret-safe authentication", ("api.request.read", "api.request.write"))

    def invoke(self, operation: str, arguments: dict[str, object]) -> dict[str, object]:
        if operation not in {"api.request.read", "api.request.write"}:
            raise ValueError(f"unsupported API operation: {operation}")
        endpoint_name = str(arguments.get("endpoint", ""))
        path = str(arguments.get("path", ""))
        endpoint = self.endpoints.get(endpoint_name)
        if endpoint is None:
            return {"ok": False, "error": "unknown API endpoint"}
        if not path.startswith("/") or path.startswith("//") or ".." in path.split("/"):
            return {"ok": False, "error": "API path is not allowlisted"}
        if endpoint.allowed_paths and not any(path == prefix or path.startswith(prefix.rstrip("/") + "/") for prefix in endpoint.allowed_paths):
            return {"ok": False, "error": "API path is not allowlisted"}
        url = urljoin(endpoint.base_url.rstrip("/") + "/", path.lstrip("/"))
        headers = {"User-Agent": "Jarvis/1.0", "Accept": "application/json", "Content-Type": "application/json"}
        if endpoint.key_env:
            key = os.environ.get(endpoint.key_env, "")
            if key:
                headers["Authorization"] = f"Bearer {key}"
        method = "GET" if operation == "api.request.read" else "POST"
        payload = arguments.get("json")
        body = json.dumps(payload).encode("utf-8") if method == "POST" and payload is not None else None
        request = Request(url, headers=headers, method=method, data=body)
        with urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read(self.max_bytes + 1)
            truncated = len(raw) > self.max_bytes
            content_type = response.headers.get("Content-Type", "")
            status = response.status
        raw = raw[: self.max_bytes]
        text = raw.decode("utf-8", errors="replace")
        try:
            data: object = json.loads(text)
        except json.JSONDecodeError:
            data = text
        return {"ok": 200 <= status < 300, "status": status, "content_type": content_type, "data": data, "truncated": truncated}
