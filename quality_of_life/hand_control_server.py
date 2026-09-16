"""Loopback-only bridge for browser webcam hand tracking."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Event, Thread
import time
from typing import Any

from .computer import ComputerController
from .hand_control import HandControlBridge, HandGestureInterpreter, HandSample
from .permissions import Capability, CapabilityPolicy

ROOT = Path(__file__).resolve().parent


class HandControlServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, *, bridge: HandControlBridge, interpreter: HandGestureInterpreter):
        super().__init__(address, handler)
        self.bridge = bridge
        self.interpreter = interpreter
        self.last_sample = time.monotonic()
        self._watchdog_stop = Event()
        self._watchdog = Thread(target=self._watchdog_loop, name="jarvis-hand-watchdog", daemon=True)
        self._watchdog.start()

    def note_sample(self) -> None:
        self.last_sample = time.monotonic()

    def _watchdog_loop(self) -> None:
        while not self._watchdog_stop.wait(0.20):
            if self.bridge.enabled and time.monotonic() - self.last_sample > 0.75:
                self.interpreter.disable()
                self.bridge.disable()

    def shutdown(self):
        self._watchdog_stop.set()
        self.interpreter.disable()
        self.bridge.disable()
        return super().shutdown()

    def server_close(self):
        self._watchdog_stop.set()
        return super().server_close()


class HandControlHandler(BaseHTTPRequestHandler):
    server: HandControlServer

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "null")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/hand-control.html"}:
            try:
                body = (ROOT / "hand-control.html").read_bytes()
            except OSError:
                self._json(500, {"error": "hand-control page unavailable"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/health":
            self._json(200, {"status": "ok", "enabled": self.server.bridge.enabled})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/hand/event", "/hand/stop"}:
            self._json(404, {"error": "not found"})
            return
        self.server.note_sample()
        if self.path == "/hand/stop":
            self.server.interpreter.disable()
            self.server.bridge.disable()
            self._json(200, {"accepted": True, "enabled": False})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 4096:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            sample = HandSample(
                x=float(payload["x"]), y=float(payload["y"]), pinch=bool(payload["pinch"]),
                fingers=int(payload["fingers"]), confidence=float(payload["confidence"]),
            )
            events = self.server.interpreter.interpret(sample)
            dispatched = sum(self.server.bridge.dispatch(event) for event in events)
            self._json(200, {"accepted": True, "events": [e.kind for e in events], "dispatched": dispatched, "enabled": self.server.bridge.enabled})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.server.interpreter.disable()
            self.server.bridge.disable()
            self._json(400, {"accepted": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self.server.interpreter.disable()
            self.server.bridge.disable()
            self._json(500, {"accepted": False, "error": f"hand control error: {exc}"})

    def log_message(self, _format: str, *_args: object) -> None:
        return


def create_server(*, enabled: bool = False, controller: Any | None = None) -> HandControlServer:
    if controller is None:
        policy = CapabilityPolicy(allowed=frozenset({Capability.MOUSE_CONTROL}))
        controller = ComputerController(policy)
    interpreter = HandGestureInterpreter()
    bridge = HandControlBridge(enabled=enabled, controller=controller)
    return HandControlServer(("127.0.0.1", 8795), HandControlHandler, bridge=bridge, interpreter=interpreter)


def main() -> None:
    import argparse
    import webbrowser

    parser = argparse.ArgumentParser(description="Jarvis local webcam hand-control bridge")
    parser.add_argument("--enabled", action="store_true")
    args = parser.parse_args()
    server = create_server(enabled=args.enabled)
    try:
        if args.enabled:
            webbrowser.open("http://127.0.0.1:8795/", new=1)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
