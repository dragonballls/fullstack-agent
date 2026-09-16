"""Optional lifecycle manager for the webcam hand-control bridge."""
from __future__ import annotations

from threading import Lock, Thread, current_thread
from typing import Any
import webbrowser


class HandControlRuntime:
    """Keep optional webcam control isolated from core Jarvis startup."""

    url = "http://127.0.0.1:8795/"

    def __init__(self, *, controller: Any | None = None, enabled: bool = False, open_browser: bool = True) -> None:
        self._controller = controller
        self._enabled = False
        self._state = "disabled"
        self._detail = "hand control is disabled until explicitly started"
        self._open_browser = open_browser
        self._lock = Lock()
        self._server: Any | None = None
        self._thread: Thread | None = None
        if enabled:
            self.start()

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def start(self) -> bool:
        with self._lock:
            if self._enabled and self._server is not None:
                return True
            try:
                from .hand_control_server import create_server
                server = create_server(enabled=True, controller=self._controller)
                thread = Thread(target=server.serve_forever, name="jarvis-hand-control", daemon=True)
                thread.start()
            except Exception as exc:  # noqa: BLE001
                self._server = None
                self._thread = None
                self._enabled = False
                self._state = "degraded"
                self._detail = f"hand-control runtime unavailable: {exc}"
                return False
            self._server = server
            self._thread = thread
            self._enabled = True
            self._state = "active"
            self._detail = "loopback hand-control bridge is running"
        if self._open_browser:
            try:
                webbrowser.open(self.url, new=1)
            except Exception:
                self._detail = "bridge is running; browser could not be opened automatically"
        return True

    def stop(self) -> None:
        with self._lock:
            server = self._server
            thread = self._thread
            self._server = None
            self._thread = None
            self._enabled = False
            self._state = "disabled"
            self._detail = "hand control is stopped"
        if server is not None:
            try:
                server.shutdown()
            finally:
                server.server_close()
        if thread is not None and thread is not current_thread():
            thread.join(timeout=1.0)

    def status(self) -> dict[str, object]:
        with self._lock:
            return {"enabled": self._enabled, "state": self._state, "detail": self._detail, "url": self.url}
