"""Bounded web research adapter for the universal tool broker."""

from __future__ import annotations

import json
import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .tool_broker import ToolManifest


class WebToolAdapter:
    def __init__(self, allowed_hosts: set[str] | None = None, *, timeout_seconds: float = 10.0, max_bytes: int = 1_000_000) -> None:
        configured = os.environ.get("JARVIS_WEB_ALLOWED_HOSTS", "")
        values = allowed_hosts if allowed_hosts is not None else {item.strip().lower() for item in configured.split(",") if item.strip()}
        self.allowed_hosts = frozenset(values)
        self.timeout_seconds = max(0.5, timeout_seconds)
        self.max_bytes = max(1_024, max_bytes)

    def manifest(self) -> ToolManifest:
        return ToolManifest("web", "Bounded HTTPS web research and configured search", ("web.fetch", "web.search"))

    def invoke(self, operation: str, arguments: dict[str, object]) -> dict[str, object]:
        if operation == "web.fetch":
            return self.fetch(str(arguments.get("url", "")))
        if operation == "web.search":
            return self.search(str(arguments.get("query", "")), int(arguments.get("limit", 5)))
        raise ValueError(f"unsupported web operation: {operation}")

    def fetch(self, url: str) -> dict[str, object]:
        parsed = self._validate_url(url)
        request = Request(url, headers={"User-Agent": "Jarvis/1.0", "Accept": "text/html,application/json,text/plain"})
        with urlopen(request, timeout=self.timeout_seconds) as response:
            content_type = response.headers.get("Content-Type", "")
            body = response.read(self.max_bytes + 1)
            truncated = len(body) > self.max_bytes
        body = body[: self.max_bytes]
        if "application/json" in content_type:
            text = body.decode("utf-8", errors="replace")
            try:
                data: object = json.loads(text)
            except json.JSONDecodeError:
                data = text
        else:
            data = body.decode("utf-8", errors="replace")
        return {"ok": True, "url": f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}", "content_type": content_type, "data": data, "truncated": truncated}

    def search(self, query: str, limit: int = 5) -> dict[str, object]:
        if not query.strip():
            raise ValueError("search query is required")
        endpoint = os.environ.get("JARVIS_WEB_SEARCH_URL", "").strip()
        if not endpoint:
            raise RuntimeError("web search is not configured; set JARVIS_WEB_SEARCH_URL")
        self._validate_url(endpoint)
        url = endpoint + ("&" if "?" in endpoint else "?") + "q=" + __import__("urllib.parse", fromlist=["quote"]).quote(query) + "&limit=" + str(max(1, min(limit, 10)))
        request = Request(url, headers={"User-Agent": "Jarvis/1.0", "Accept": "application/json"})
        key_env = os.environ.get("JARVIS_WEB_SEARCH_API_KEY_ENV", "").strip()
        if key_env:
            key = os.environ.get(key_env, "")
            if key:
                request.add_header("Authorization", f"Bearer {key}")
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = response.read(self.max_bytes).decode("utf-8", errors="replace")
        parsed = json.loads(payload)
        results = parsed.get("results", []) if isinstance(parsed, dict) else []
        normalized = []
        for item in results[:10]:
            if isinstance(item, dict):
                normalized.append({"title": str(item.get("title", "")), "url": str(item.get("url", "")), "snippet": str(item.get("snippet", ""))})
        return {"ok": True, "results": normalized}

    def _validate_url(self, url: str):
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("only credential-free HTTPS URLs are allowed")
        host = parsed.hostname.lower() if parsed.hostname else ""
        if self.allowed_hosts and not any(host == allowed or host.endswith("." + allowed) for allowed in self.allowed_hosts):
            raise ValueError("web destination is not allowlisted")
        return parsed

    def _parse_response(self, text: str) -> dict[str, object]:
        truncated = len(text) > self.max_bytes
        return {"body": text[: self.max_bytes], "truncated": truncated}
