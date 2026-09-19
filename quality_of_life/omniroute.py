"""Automatic local OmniRoute lifecycle and connectivity support for Jarvis.

Jarvis treats OmniRoute as a local OpenAI-compatible gateway. The connector is
lazy: it first probes the configured /v1/models endpoint and, when enabled,
starts the local `omniroute` command without opening a console window.
"""

from __future__ import annotations

import ipaddress
import os
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .omniroute_setup import OmniRouteProvisioner


def is_loopback_hostname(hostname: str | None) -> bool:
    """Return whether a hostname is localhost or a syntactic loopback address."""
    if not hostname:
        return False
    normalized = hostname.strip().lower().rstrip(".")
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


class OmniRouteConnection:
    """Keep a local OmniRoute endpoint available without owning its shutdown."""

    def __init__(self, base_url: str, api_key_env: str, *, timeout_seconds: float = 2.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.timeout_seconds = max(0.5, float(timeout_seconds))
        self._lock = threading.Lock()
        self._ready = False
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def enabled(self) -> bool:
        return os.environ.get("JARVIS_OMNIROUTE_AUTOSTART", "1").strip().lower() not in {
            "0", "false", "no", "off"
        }

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        key = os.environ.get(self.api_key_env, "").strip()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def probe(self) -> bool:
        """Return True when OmniRoute responds to its OpenAI-compatible models endpoint."""
        url = self.base_url + "/models"
        request = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                if not 200 <= int(response.status) < 300:
                    return False
                return bool(response.read(1))
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    @staticmethod
    def _command() -> list[str]:
        configured = os.environ.get("JARVIS_OMNIROUTE_COMMAND", "omniroute").strip()
        if not configured:
            return ["omniroute"]
        return configured.split()

    def _start(self) -> bool:
        configured_command = os.environ.get("JARVIS_OMNIROUTE_COMMAND", "").strip()
        provisioner = OmniRouteProvisioner(self.base_url)
        if configured_command:
            command = self._command()
            executable = shutil.which(command[0])
            if executable is None and not os.path.isfile(command[0]):
                return False
            if executable and len(command) == 1:
                command[0] = executable
        else:
            try:
                command = provisioner.command_argv()
            except RuntimeError:
                return False
        env = provisioner.environment()
        parsed = urllib.parse.urlparse(self.base_url)
        env["PORT"] = str(parsed.port or 20128)
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                creationflags=creationflags,
                close_fds=True,
            )
        except (OSError, ValueError):
            self._process = None
            return False
        return True

    def ensure_ready(self, *, wait_seconds: float = 15.0) -> bool:
        """Probe, then lazily start OmniRoute and wait briefly for its API."""
        if self._ready and self.probe():
            return True
        with self._lock:
            if self.probe():
                self._ready = True
                return True
            if not self.enabled or not is_loopback_hostname(urllib.parse.urlparse(self.base_url).hostname):
                return False
            if self._process is None or self._process.poll() is not None:
                if not self._start():
                    return False
            deadline = time.monotonic() + max(0.5, wait_seconds)
            while time.monotonic() < deadline:
                if self.probe():
                    self._ready = True
                    return True
                if self._process is not None and self._process.poll() is not None:
                    break
                time.sleep(0.25)
        return False

    def status(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "base_url": self.base_url,
            "ready": bool(self._ready and self.probe()),
            "started_by_jarvis": self._process is not None,
            "process_running": self._process is not None and self._process.poll() is None,
        }
