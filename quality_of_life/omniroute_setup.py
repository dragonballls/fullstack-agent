"""Provision and operate the pinned OmniRoute runtime shipped with Jarvis.

The release build embeds a portable Node.js 24 runtime plus OmniRoute 3.8.50.
Jarvis extracts those resources into the normal PyInstaller temporary directory
and runs OmniRoute headlessly, while provider credentials remain inside
OmniRoute's own encrypted/local credential store. Development installs may use
an existing OmniRoute/Node installation or perform a user-local npm install.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


OMNIROUTE_VERSION = "3.8.50"
NODE_VERSION = "24.21.0"
OMNIROUTE_PACKAGE = f"omniroute@{OMNIROUTE_VERSION}"
DEFAULT_PORT = 20128
PROVISION_TIMEOUT_SECONDS = max(30, int(os.environ.get("JARVIS_OMNIROUTE_PROVISION_TIMEOUT", "300")))


def _is_windows() -> bool:
    return sys.platform == "win32"


# Only unambiguous public key formats are auto-detected. Ambiguous keys are
# never sent to multiple providers merely to discover which one accepts them.
_KEY_PREFIX_PROVIDERS: tuple[tuple[str, str], ...] = (
    ("sk-ant-", "anthropic"),
    ("sk-or-v1-", "openrouter"),
    ("gsk_", "groq"),
    ("xai-", "xai"),
    ("AIza", "gemini"),
    ("csk-", "cerebras"),
    ("sk-proj-", "openai"),
    ("sk-svcacct-", "openai"),
)


def detect_provider_from_key(api_key: str) -> str | None:
    key = str(api_key or "").strip()
    if not key:
        return None
    lowered = key.lower()
    for prefix, provider in _KEY_PREFIX_PROVIDERS:
        if lowered.startswith(prefix.lower()):
            return provider
    return None



def default_data_dir() -> Path:
    override = os.environ.get("JARVIS_OMNIROUTE_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if _is_windows():
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / "Jarvis" / "OmniRoute"
    return Path.home() / ".local" / "share" / "Jarvis" / "OmniRoute"


def _split_command(value: str) -> list[str]:
    return shlex.split(value, posix=not _is_windows())


def _packaged_runtime_root() -> Path | None:
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return None
    root = Path(base) / "omniroute_runtime"
    return root if root.is_dir() else None


@dataclass(frozen=True)
class OmniRouteRuntimeStatus:
    available: bool
    source: str
    version: str | None
    base_url: str
    data_dir: str
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "source": self.source,
            "version": self.version,
            "base_url": self.base_url,
            "data_dir": self.data_dir,
            "reason": self.reason,
        }


class OmniRouteProvisioner:
    """Resolve the bundled OmniRoute first, then safe local development fallbacks."""

    def __init__(self, base_url: str = f"http://127.0.0.1:{DEFAULT_PORT}/v1", data_dir: Path | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.data_dir = (data_dir or default_data_dir()).expanduser()
        self._resolved: tuple[str, ...] | None = None
        self._source = "unavailable"
        self._process: subprocess.Popen[bytes] | None = None
        self._owner_file = self.data_dir / "jarvis-owner.json"

    @property
    def port(self) -> int:
        parsed = urllib.parse.urlparse(self.base_url)
        return int(parsed.port or DEFAULT_PORT)

    def _packaged_command(self) -> tuple[str, ...] | None:
        root = _packaged_runtime_root()
        if root is None:
            return None
        node = root / ("node.exe" if _is_windows() else Path("bin") / "node")
        if not node.is_file():
            return None
        entry = root / "node_modules" / "omniroute" / "bin" / "omniroute.mjs"
        if not entry.is_file():
            return None
        return (str(node), str(entry))

    def _local_install_command(self) -> tuple[str, ...] | None:
        if _is_windows():
            binary = self.data_dir / "node_modules" / ".bin" / "omniroute.cmd"
        else:
            binary = self.data_dir / "node_modules" / ".bin" / "omniroute"
        if binary.is_file():
            return (str(binary),)
        return None

    def _system_command(self) -> tuple[str, ...] | None:
        configured = os.environ.get("JARVIS_OMNIROUTE_COMMAND", "").strip()
        if configured:
            argv = _split_command(configured)
            return tuple(argv) if argv else None
        found = shutil.which("omniroute")
        return (found,) if found else None

    def _node_and_npm(self) -> tuple[str, str] | None:
        node = os.environ.get("JARVIS_NODE_COMMAND") or shutil.which("node")
        npm = os.environ.get("JARVIS_NPM_COMMAND")
        if not npm:
            npm = shutil.which("npm.cmd" if _is_windows() else "npm") or shutil.which("npm")
        if not node or not npm:
            return None
        return node, npm

    @staticmethod
    def _version(argv: tuple[str, ...], env: dict[str, str]) -> str | None:
        try:
            result = subprocess.run(
                [*argv, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                env=env,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        text = (result.stdout or "").strip()
        return text.splitlines()[-1].strip() if text else None

    def _npm_install(self) -> tuple[str, ...] | None:
        tools = self._node_and_npm()
        if tools is None:
            return None
        _node, npm = tools
        self.data_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["DATA_DIR"] = str(self.data_dir)
        env["NODE_ENV"] = "production"
        package_json = self.data_dir / "package.json"
        command = [
            npm,
            "install",
            "--prefix",
            str(self.data_dir),
            "--no-fund",
            "--no-audit",
            "--omit=dev",
            OMNIROUTE_PACKAGE,
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=PROVISION_TIMEOUT_SECONDS,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            return None
        if not package_json.is_file():
            return None
        return self._local_install_command()

    def resolve_command(self, *, install_if_missing: bool = True) -> tuple[str, ...]:
        if self._resolved:
            return self._resolved

        packaged = self._packaged_command()
        if packaged:
            self._resolved = packaged
            self._source = "bundled"
            return packaged

        local = self._local_install_command()
        if local:
            self._resolved = local
            self._source = "user-local"
            return local

        system = self._system_command()
        if system:
            self._resolved = system
            self._source = "system"
            return system

        if install_if_missing:
            local = self._npm_install()
            if local:
                self._resolved = local
                self._source = "user-local"
                return local

        raise RuntimeError(
            "OmniRoute runtime is unavailable. Jarvis normally ships a bundled "
            f"OmniRoute {OMNIROUTE_VERSION} runtime; this development environment "
            "has neither the bundled runtime nor Node/npm available."
        )

    def command_argv(self, *, install_if_missing: bool = True, for_start: bool = False) -> list[str]:
        command = list(self.resolve_command(install_if_missing=install_if_missing))
        if for_start and "--no-open" not in command:
            command.append("--no-open")
        return command

    def environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env["DATA_DIR"] = str(self.data_dir)
        env["PORT"] = str(self.port)
        env["OMNIROUTE_TELEMETRY"] = env.get("OMNIROUTE_TELEMETRY", "false")
        return env

    def _probe(self) -> bool:
        parsed = urllib.parse.urlparse(self.base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        for url in (self.base_url + "/models", origin + "/api/monitoring/health", origin + "/healthz"):
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET"),
                    timeout=1.5,
                ) as response:
                    if 200 <= int(response.status) < 300:
                        return True
            except urllib.error.HTTPError as exc:
                if exc.code in {401, 403, 405}:
                    return True
            except (urllib.error.URLError, TimeoutError, OSError):
                continue
        return False

    def _read_owner(self) -> dict[str, object] | None:
        try:
            payload = json.loads(self._owner_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _owner_pid_alive(pid: object) -> bool:
        try:
            value = int(pid)
        except (TypeError, ValueError):
            return False
        if value <= 0:
            return False
        if _is_windows():
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            SYNCHRONIZE = 0x00100000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, value)
            if not handle:
                return False
            try:
                STILL_ACTIVE = 259
                exit_code = ctypes.c_ulong()
                if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return False
                return int(exit_code.value) == STILL_ACTIVE
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        try:
            os.kill(value, 0)
        except (OSError, ProcessLookupError, PermissionError):
            return False
        return True

    def _managed_server_available(self) -> bool:
        owner = self._read_owner()
        if not owner or owner.get("owner") != "jarvis":
            return False
        if str(owner.get("base_url", "")).rstrip("/") != self.base_url:
            return False
        return self._owner_pid_alive(owner.get("pid"))

    def _write_owner(self, pid: int) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "owner": "jarvis",
            "pid": int(pid),
            "base_url": self.base_url,
            "port": self.port,
            "created_at": time.time(),
        }
        tmp = self._owner_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self._owner_file)

    def _clear_owner(self) -> None:
        try:
            owner = self._read_owner()
            if owner and int(owner.get("pid", -1)) == (self._process.pid if self._process is not None else -2):
                self._owner_file.unlink(missing_ok=True)
        except (TypeError, ValueError, OSError):
            pass

    def probe_only(self) -> bool:
        return self._probe()

    def ensure_running(self, *, wait_seconds: float = 15.0) -> bool:
        if self._probe():
            if self._managed_server_available() or (
                self._process is not None and self._process.poll() is None
            ):
                return True
            raise RuntimeError(
                f"An unmanaged OmniRoute instance is already serving {self.base_url}. "
                "Jarvis will not configure a different data directory into a running gateway."
            )

        command = self.command_argv()
        if self._process is not None and self._process.poll() is None:
            process = self._process
        else:
            process = subprocess.Popen(
                command + ["--port", str(self.port)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=self.environment(),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                close_fds=True,
            )
            self._process = process
            self._write_owner(process.pid)

        deadline = time.monotonic() + max(0.5, float(wait_seconds))
        while time.monotonic() < deadline:
            if self._probe():
                return True
            if process.poll() is not None:
                self._clear_owner()
                break
            time.sleep(0.25)
        if process.poll() is not None:
            self._clear_owner()
        return False

    def status(self) -> OmniRouteRuntimeStatus:
        try:
            argv = self.resolve_command(install_if_missing=False)
        except RuntimeError as exc:
            return OmniRouteRuntimeStatus(
                False,
                "unavailable",
                None,
                self.base_url,
                str(self.data_dir),
                str(exc),
            )
        version = self._version(argv, self.environment())
        available = version is not None
        reason = None if available else "OmniRoute command was found but version validation failed"
        return OmniRouteRuntimeStatus(
            available,
            self._source,
            version,
            self.base_url,
            str(self.data_dir),
            reason,
        )

    def configure_provider(self, provider: str, api_key: str) -> dict[str, object]:
        normalized = provider.strip().lower()
        key = api_key.strip()
        if normalized in {"", "auto", "detect"}:
            normalized = detect_provider_from_key(key) or ""
            if not normalized:
                raise ValueError(
                    "This API key format cannot be safely auto-detected. "
                    "Choose its OmniRoute provider explicitly."
                )
        if not normalized or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_-." for ch in normalized):
            raise ValueError("provider must contain only letters, numbers, underscore, hyphen, or dot")
        if len(key) < 8:
            raise ValueError("provider API key is too short")
        command = self.command_argv()
        env = self.environment()
        add_command = [*command, "--non-interactive", "providers", "add", normalized, "--credential-stdin"]
        result = subprocess.run(
            add_command,
            input=key + "\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=PROVISION_TIMEOUT_SECONDS,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            # Never expose command output because a provider could echo sensitive material.
            raise RuntimeError("OmniRoute rejected the provider credential or is not initialized yet")
        return {"ok": True, "provider": normalized, "configured": True}

    def list_providers(self, *, install_if_missing: bool = True) -> list[dict[str, object]]:
        command = self.command_argv(install_if_missing=install_if_missing)
        result = subprocess.run(
            [*command, "--non-interactive", "providers", "list", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env=self.environment(),
            check=False,
        )
        if result.returncode != 0:
            return []
        raw = (result.stdout or "").strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return []
        items = payload.get("connections", payload.get("providers", payload)) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            return []
        cleaned: list[dict[str, object]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("provider") or item.get("id")
            status = item.get("status") or item.get("state")
            if name:
                cleaned.append({"name": str(name), "status": str(status or "configured")})
        return cleaned

    def test_provider(self, provider: str) -> dict[str, object]:
        normalized = provider.strip().lower()
        if not normalized:
            raise ValueError("provider is required")
        command = self.command_argv()
        result = subprocess.run(
            [*command, "--non-interactive", "providers", "test", normalized],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=PROVISION_TIMEOUT_SECONDS,
            env=self.environment(),
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "provider": normalized,
            "tested": True,
            "message": "Provider test passed" if result.returncode == 0 else "Provider test failed",
        }

    def start(self) -> bool:
        try:
            return self.ensure_running(wait_seconds=15.0)
        except RuntimeError:
            return False
