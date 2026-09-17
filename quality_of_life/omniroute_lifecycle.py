from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request


class OmniRouteLifecycle:
    """Keep the documented local OmniRoute gateway available when installed."""

    def __init__(
        self,
        base_url: str,
        *,
        command: str | None = None,
        startup_timeout: float = 15.0,
        poll_interval: float = 0.25,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.command = (command or os.environ.get("JARVIS_OMNIROUTE_COMMAND", "omniroute --no-open")).strip()
        self.startup_timeout = max(1.0, float(startup_timeout))
        self.poll_interval = max(0.05, float(poll_interval))

    @staticmethod
    def _is_loopback(base_url: str) -> bool:
        hostname = urllib.parse.urlparse(base_url).hostname
        return bool(hostname and hostname.lower().rstrip(".") in {"localhost", "127.0.0.1", "::1"})

    def _probe(self) -> bool:
        parsed = urllib.parse.urlparse(self.base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        for url in (origin + "/", origin + "/api/monitoring/health"):
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET"),
                    timeout=1.5,
                ):
                    return True
            except urllib.error.HTTPError as exc:
                if 200 <= exc.code < 500:
                    return True
            except (urllib.error.URLError, TimeoutError, OSError):
                continue
        return False

    def _command_argv(self) -> list[str]:
        configured = self.command
        argv = shlex.split(configured, posix=os.name != "nt")
        if not argv:
            raise RuntimeError("OmniRoute startup command is empty")
        resolved = shutil.which(argv[0])
        if resolved:
            argv[0] = resolved
            return argv
        if os.path.isfile(argv[0]):
            return argv
        raise RuntimeError(
            f"OmniRoute is not running at {self.base_url} and the '{argv[0]}' command was not found"
        )

    def ensure_available(self) -> bool:
        """Probe, then silently start a local OmniRoute CLI if needed."""
        if not self._is_loopback(self.base_url) or self._probe():
            return True

        process = subprocess.Popen(
            self._command_argv(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            close_fds=True,
        )
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self._probe():
                return True
            if process.poll() is not None:
                raise RuntimeError(
                    f"OmniRoute exited before becoming ready (code {process.returncode})"
                )
            time.sleep(self.poll_interval)

        try:
            process.terminate()
        except OSError:
            pass
        raise RuntimeError(
            f"OmniRoute did not become ready at {self.base_url} within {self.startup_timeout:g}s"
        )
