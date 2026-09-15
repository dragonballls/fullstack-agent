"""Loopback-only HTTP bridge for browser webcam hand tracking."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any

from .computer import ComputerController
from .hand_control import HandControlBridge, HandGestureInterpreter, HandSample
from .permissions import Capability, CapabilityPolicy


ROOT = Path(__file__).resolve().parent


class HandControlHandler(BaseHTTPRequestHandler):
    interpreter: HandGestureInterpreter | None = None
    bridge: HandControlBridge | None = None

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/hand-control.html"}:
            body = (ROOT / "hand-control.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/health":
            self._json(200, {"status": "ok", "enabled": bool(self.bridge and self.bridge.enabled)})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/hand/event", "/hand/stop"}:
            self._json(404, {"error": "not found"})
            return
        if self.bridge is None or self.interpreter is None:
            self._json(503, {"error": "hand control unavailable"})
            return
        if self.path == "/hand/stop":
            self.interpreter.disable()
            self.bridge.disable()
            self._json(200, {"accepted": True, "enabled": False})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 4096:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            sample = HandSample(
                x=float(payload["x"]),
                y=float(payload["y"]),
                pinch=bool(payload["pinch"]),
                fingers=int(payload["fingers"]),
                confidence=float(payload["confidence"]),
            )
            timestamp = float(payload.get("timestamp", 0.0)) if "timestamp" in payload else None
            events = self.interpreter.interpret(sample, timestamp=timestamp)
            dispatched = sum(self.bridge.dispatch(event) for event in events)
            self._json(200, {"accepted": True, "events": [event.kind for event in events], "dispatched": dispatched, "enabled": self.bridge.enabled})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self._json(400, {"accepted": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            # A camera/input failure must never crash the server process.
            self._json(500, {"accepted": False, "error": f"hand control error: {exc}"})

    def log_message(self, _format: str, *_args: object) -> None:
        return


def create_server(*, enabled: bool = False, controller: Any | None = None) -> ThreadingHTTPServer:
    if controller is None:
        policy = CapabilityPolicy(allowed=frozenset({Capability.MOUSE_CONTROL}))
        controller = ComputerController(policy)
    HandControlHandler.interpreter = HandGestureInterpreter()
    HandControlHandler.bridge = HandControlBridge(enabled=enabled, controller=controller)
    return ThreadingHTTPServer(("127.0.0.1", 8795), HandControlHandler)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Jarvis local webcam hand-control bridge")
    parser.add_argument("--enabled", action="store_true", help="enable OS pointer control when the page connects")
    args = parser.parse_args()
    server = create_server(enabled=args.enabled)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if HandControlHandler.bridge is not None:
            HandControlHandler.bridge.disable()
        server.server_close()


if __name__ == "__main__":
    main()
