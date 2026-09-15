"""Optional lifecycle manager for the webcam hand-control bridge."""

from __future__ import annotations

from threading import Lock, Thread
from typing import Any
import webbrowser


class HandControlRuntime:
    """Keep the optional hand-control server isolated from core Jarvis startup."""

    url = "http://127.0.0.1:8795/"

    def __init__(self, *, controller: Any | None = None, enabled: bool = False) -> None:
        self._controller = controller
        self._enabled = False
        self._lock = Lock()
        self._server: Any | None = None
        self._thread: Thread | None = None
        if enabled:
            self.start()

    @property
    def enabled(self) -> bool:
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
            except Exception:
                self._server = None
                self._thread = None
                self._enabled = False
                return False
            self._server = server
            self._thread = thread
            self._enabled = True
        try:
            webbrowser.open(self.url, new=1)
        except Exception:
            pass
        return True

    def stop(self) -> None:
        with self._lock:
            server = self._server
            self._server = None
            self._thread = None
            self._enabled = False
        if server is not None:
            try:
                server.shutdown()
            finally:
                server.server_close()

    def status(self) -> dict[str, object]:
        return {"enabled": self._enabled, "url": self.url}
