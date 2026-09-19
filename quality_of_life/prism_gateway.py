"""Windows-native lifecycle manager for the optional Prism/free-astra bridge.

The bridge contains no local LLM. It is only an OpenAI-compatible adapter whose
inference remains on the remote Prism service. Jarvis starts it in-process so the
single-file Windows executable needs no Bash/PowerShell console.

A Prism session file must already be configured by the user. Jarvis deliberately
does not scrape browser cookies or silently collect credentials.
"""

from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path
import threading
import time
from typing import Any
import urllib.error
import urllib.request

LOGGER = logging.getLogger("jarvis.prism")


class PrismGateway:
    """Own the optional embedded free-astra HTTP bridge lifecycle."""

    HOST = "127.0.0.1"
    DEFAULT_PORT = 8319
    SESSION_ENV = "JARVIS_PRISM_SESSION"
    ENABLE_ENV = "JARVIS_PRISM_ENABLED"
    HOME_ENV = "JARVIS_PRISM_HOME"

    def __init__(self, *, port: int | None = None, session_file: str | Path | None = None) -> None:
        self.port = int(port or os.environ.get("JARVIS_PRISM_PORT", str(self.DEFAULT_PORT)))
        self.home = self._default_home()
        self.session_file = Path(
            session_file
            or os.environ.get(self.SESSION_ENV, "")
            or (self.home / "session.json")
        ).expanduser()
        self._lock = threading.RLock()
        self._server: Any | None = None
        self._thread: threading.Thread | None = None
        self._module: Any | None = None
        self._started = False

    @classmethod
    def _default_home(cls) -> Path:
        explicit = os.environ.get(cls.HOME_ENV, "").strip()
        if explicit:
            return Path(explicit).expanduser()
        if os.name == "nt":
            root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            return root / "Jarvis" / "Prism"
        return Path.home() / ".local" / "share" / "Jarvis" / "Prism"

    @classmethod
    def enabled(cls) -> bool:
        return os.environ.get(cls.ENABLE_ENV, "1").strip().lower() not in {
            "0", "false", "no", "off"
        }

    @property
    def configured(self) -> bool:
        return self.session_file.is_file()

    @property
    def base_url(self) -> str:
        return f"http://{self.HOST}:{self.port}/v1"

    def _vendor_path(self) -> Path:
        frozen_root = getattr(__import__("sys"), "_MEIPASS", None)
        if frozen_root:
            candidate = Path(frozen_root) / "free_astra" / "freeastra.py"
        else:
            candidate = Path(__file__).resolve().parents[1] / "third_party" / "free_astra" / "freeastra.py"
        return candidate

    def _load_module(self) -> Any:
        if self._module is not None:
            return self._module
        path = self._vendor_path()
        if not path.is_file():
            raise RuntimeError(f"Embedded free-astra bridge is missing: {path}")
        os.environ["FREE_ASTRA_HOME"] = str(self.home)
        os.environ["PRISM_SESSION"] = str(self.session_file)
        os.environ["PRISM_PORT"] = str(self.port)
        # The upstream project offers Unix/Bash browser refresh helpers. The
        # packaged Windows path intentionally does not invoke those helpers.
        os.environ["PRISM_NO_AUTO_REFRESH"] = "1"
        spec = importlib.util.spec_from_file_location("jarvis_embedded_free_astra", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load embedded free-astra bridge")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._module = module
        return module

    def _probe(self) -> bool:
        request = urllib.request.Request(
            self.base_url + "/models",
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=1.5) as response:
                return 200 <= int(response.status) < 300
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def ensure_started(self, *, wait_seconds: float = 8.0) -> bool:
        """Start the embedded bridge when configured and wait for its HTTP API."""
        if not self.enabled() or not self.configured:
            return False
        if self._probe():
            self._started = True
            return True

        with self._lock:
            if self._probe():
                self._started = True
                return True
            if self._thread is None or not self._thread.is_alive():
                module = self._load_module()
                try:
                    module.load_session()
                except (OSError, ValueError, KeyError, RuntimeError, SystemExit) as exc:
                    LOGGER.warning("Prism bridge session is unavailable: %s", str(exc)[:300])
                    return False
                module.UPSTREAM = module.pick_upstream()
                try:
                    module.SERVER = module.ThreadingHTTPServer(
                        (self.HOST, self.port), module.Handler
                    )
                except OSError as exc:
                    LOGGER.warning("Could not bind Prism bridge on %s: %s", self.base_url, exc)
                    return False

                def serve() -> None:
                    try:
                        module.SERVER.serve_forever(poll_interval=0.5)
                    except Exception:
                        LOGGER.exception("Embedded Prism bridge stopped unexpectedly")
                    finally:
                        try:
                            module.SERVER.server_close()
                        except Exception:
                            pass

                self._server = module.SERVER
                self._thread = threading.Thread(
                    target=serve, name="jarvis-prism-gateway", daemon=True
                )
                self._thread.start()
                try:
                    period = float(os.environ.get("PRISM_KEEPALIVE", "600"))
                    if period > 0:
                        threading.Thread(
                            target=module.keepalive_loop,
                            name="jarvis-prism-keepalive",
                            daemon=True,
                        ).start()
                except Exception:
                    LOGGER.debug("Prism keepalive thread could not start", exc_info=True)

            deadline = time.monotonic() + max(0.5, float(wait_seconds))
            while time.monotonic() < deadline:
                if self._probe():
                    self._started = True
                    return True
                time.sleep(0.2)
        return False

    def stop(self) -> None:
        with self._lock:
            server = self._server
            self._server = None
            self._started = False
            if server is not None:
                try:
                    server.shutdown()
                except Exception:
                    LOGGER.debug("Prism bridge shutdown failed", exc_info=True)
                try:
                    server.server_close()
                except Exception:
                    LOGGER.debug("Prism bridge close failed", exc_info=True)

    def status(self) -> dict[str, object]:
        ready = self._probe()
        return {
            "enabled": self.enabled(),
            "configured": self.configured,
            "ready": ready,
            "host": self.HOST,
            "port": self.port,
            "base_url": self.base_url,
            "session_file": str(self.session_file),
            "inference": "remote",
            "model": "prism-astra",
        }

    def probe_model(self, model: str = "prism-astra", timeout: float = 30.0) -> dict[str, object]:
        """Perform an explicit live capability test; never runs automatically."""
        if not self.ensure_started(wait_seconds=8):
            return {"ok": False, "model": model, "message": "Prism bridge is not configured or ready"}
        import json
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": "Reply with exactly: prism-ready"}],
        }).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            return {
                "ok": isinstance(content, str) and bool(content.strip()),
                "model": model,
                "resolved_model": data.get("model"),
                "latency_ms": int((time.monotonic() - started) * 1000),
            }
        except Exception as exc:
            return {
                "ok": False,
                "model": model,
                "message": str(exc)[:300],
                "latency_ms": int((time.monotonic() - started) * 1000),
            }
