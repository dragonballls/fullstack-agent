"""Native Windows Fullstack Agent host for Jarvis.

The Jarvis runtime remains the only planner/tool executor. This host adds the
original Fullstack Agent presentation/voice layer without using its Claude
brain. The obsolete 640x118 Tk chat bar is intentionally gone.
"""

from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from typing import Any

from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.runtime import JarvisRuntime
from quality_of_life.self_update import SelfUpdateError, build_windows_handoff_script, fetch_latest_release, is_update_available, stage_update

from scripts.fullstack_assets import embedded_path
try:
    from quality_of_life.build_info import BUILD_COMMIT
except ImportError:
    BUILD_COMMIT = "dev"

LOG_DIR = Path.home() / "AppData" / "Local" / "Jarvis" / "logs"
LOG_FILE = LOG_DIR / "desktop.log"
AUTO_UPDATE_INTERVAL = max(60, int(os.environ.get("JARVIS_AUTO_UPDATE_INTERVAL", "300")))


def _logger() -> logging.Logger:
    logger = logging.getLogger("jarvis.fullstack")
    if logger.handlers:
        return logger
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    except OSError:
        logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


LOGGER = _logger()


def build_runtime() -> JarvisRuntime:
    return JarvisRuntime(CapabilityPolicy())


class JarvisDesktopController:
    """Thin adapter preserving the existing guarded Jarvis orchestrator."""

    def __init__(self, runtime: JarvisRuntime | None = None) -> None:
        self.runtime = runtime or build_runtime()
        self.orchestrator = self.runtime._assistant_orchestrator()

    def execute_request(self, text: str, confirmed: bool = False) -> Any:
        text = text.strip()
        if not text:
            raise ValueError("request cannot be empty")
        return self.orchestrator.execute(text, confirmed=confirmed)

    def close(self) -> None:
        try:
            self.runtime.stop_health_monitor()
        except Exception:
            LOGGER.exception("failed to close Jarvis runtime")


class VisualizerAdapter:
    """Runs the upstream ai-visualizer server contract in-process."""

    def __init__(self, port: int = 8790) -> None:
        self.port = port
        self.server: Any | None = None
        self.module: Any | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        source = embedded_path("ai-visualizer/source/server.py")
        spec = importlib.util.spec_from_file_location("jarvis_embedded_visualizer", source)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load embedded visualizer server")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.CFG["name"] = os.environ.get("JARVIS_NAME", "JARVIS")
        module.CFG["face"] = os.environ.get("JARVIS_FACE", "board")
        module.CFG["port"] = self.port
        bus = os.environ.get("JARVIS_SIGNAL_DIR", "")
        if bus:
            module.BUS = Path(bus).expanduser()
        from http.server import ThreadingHTTPServer
        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), module.Handler)
        self.server.daemon_threads = True
        self.module = module
        self.thread = threading.Thread(target=self.server.serve_forever, name="jarvis-visualizer", daemon=True)
        self.thread.start()
        LOGGER.info("embedded visualizer started on 127.0.0.1:%s", self.port)

    def stop(self) -> None:
        server, thread = self.server, self.thread
        self.server = None
        self.thread = None
        if server is not None:
            try:
                server.shutdown()
            finally:
                server.server_close()
        if thread is not None and thread.is_alive():
            thread.join(timeout=3)

    def url(self) -> str:
        face = os.environ.get("JARVIS_FACE", "board")
        return f"http://127.0.0.1:{self.port}/faces/{face}/"


class VoiceAdapter:
    """Lazy bridge to the embedded upstream backtalk ears/mouth."""

    def __init__(self, controller: JarvisDesktopController) -> None:
        self.controller = controller
        self.bridge: Any | None = None

    def start(self) -> None:
        if os.environ.get("JARVIS_DISABLE_VOICE", "0").strip().lower() in {"1", "true", "yes", "on"}:
            LOGGER.info("voice disabled by configuration")
            return
        from scripts.jarvis_voice_bridge import JarvisVoiceBridge
        self.bridge = JarvisVoiceBridge(self.controller)
        self.bridge.start()

    def stop(self) -> None:
        if self.bridge is not None:
            self.bridge.stop()
            self.bridge = None


class HandsAdapter:
    """Expose the existing guarded hand-control runtime without implicit activation."""

    def __init__(self, runtime: JarvisRuntime) -> None:
        self.runtime = runtime
        self.started = False

    def start(self) -> None:
        if os.environ.get("JARVIS_ENABLE_HANDS", "0").strip().lower() not in {"1", "true", "yes", "on"}:
            LOGGER.info("hand control remains disabled until explicitly enabled")
            return
        try:
            self.runtime.dispatch(Capability.MOUSE_CONTROL, "hand_control.start")
            self.started = True
        except Exception:
            LOGGER.exception("hand control could not start")

    def stop(self) -> None:
        if not self.started:
            return
        try:
            self.runtime.dispatch(Capability.MOUSE_CONTROL, "hand_control.stop")
        except Exception:
            LOGGER.exception("hand control could not stop cleanly")
        finally:
            self.started = False


class AutoUpdateController:
    """Poll the verified rolling GitHub release and hand off a replacement safely."""

    def __init__(self, stop_event: threading.Event, request_exit: callable | None = None) -> None:
        self.stop_event = stop_event
        self.request_exit = request_exit
        self.thread: threading.Thread | None = None
        self.triggered = False

    @property
    def enabled(self) -> bool:
        return (
            sys.platform == "win32"
            and bool(getattr(sys, "frozen", False))
            and os.environ.get("JARVIS_AUTO_UPDATE", "1").strip().lower() not in {"0", "false", "no", "off"}
            and os.environ.get("JARVIS_SMOKE", "0").strip().lower() not in {"1", "true", "yes", "on"}
        )

    def start(self) -> None:
        if not self.enabled or (self.thread and self.thread.is_alive()):
            return
        self.thread = threading.Thread(target=self._loop, name="jarvis-auto-updater", daemon=True)
        self.thread.start()
        LOGGER.info("auto-update monitor enabled; build=%s interval=%ss", BUILD_COMMIT, AUTO_UPDATE_INTERVAL)

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread is not None and self.thread.is_alive() and threading.current_thread() is not self.thread:
            self.thread.join(timeout=3)

    def _loop(self) -> None:
        self.stop_event.wait(min(30, AUTO_UPDATE_INTERVAL))
        while not self.stop_event.is_set():
            if self._check_once():
                return
            self.stop_event.wait(AUTO_UPDATE_INTERVAL)

    def _check_once(self) -> bool:
        if self.triggered:
            return True
        try:
            release = fetch_latest_release()
            if not is_update_available(BUILD_COMMIT, release.commit_sha):
                return False
            update_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Jarvis" / "updates"
            staged = update_dir / f"Jarvis-{release.commit_sha[:12]}.exe"
            stage_update(release.asset_url, release.sha256, staged)
            script_path = Path(tempfile.gettempdir()) / f"Jarvis-update-{os.getpid()}-{release.commit_sha[:12]}.ps1"
            escaped_script = str(script_path).replace("'", "''")
            script_path.write_text(
                build_windows_handoff_script(os.getpid(), Path(sys.executable), staged) + f"\nRemove-Item -LiteralPath '{escaped_script}' -Force -ErrorAction SilentlyContinue\n",
                encoding="utf-8",
            )
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(script_path)],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                close_fds=True,
            )
            self.triggered = True
            self.stop_event.set()
            LOGGER.info("verified Jarvis update staged for commit %s; restarting", release.commit_sha)
            if self.request_exit is not None:
                self.request_exit()
            return True
        except SelfUpdateError as exc:
            LOGGER.warning("auto-update check failed safely: %s", exc)
        except Exception:
            LOGGER.exception("unexpected auto-update failure; current Jarvis remains running")
        return False


class FullstackJarvisHost:
    """Lifecycle supervisor for the complete Jarvis Fullstack presentation."""

    def __init__(self, controller: JarvisDesktopController, *, visualizer: Any | None = None, voice: Any | None = None, hands: Any | None = None) -> None:
        self.controller = controller
        self.visualizer = visualizer or VisualizerAdapter()
        self.voice = voice or VoiceAdapter(controller)
        self.hands = hands or HandsAdapter(controller.runtime)
        self.started = False
        self.stopped = False
        self._window: Any | None = None
        self._update_stop = threading.Event()
        self.updater = AutoUpdateController(self._update_stop, self._exit_for_update)

    @staticmethod
    def _exit_for_update() -> None:
        logging.shutdown()
        os._exit(0)

    def start(self) -> None:
        if self.started:
            return
        self.visualizer.start()
        try:
            self.voice.start()
            self.hands.start()
            self.updater.start()
        except Exception:
            self.visualizer.stop()
            raise
        self.started = True
        self.stopped = False

    def stop(self) -> None:
        if self.stopped:
            return
        self.updater.stop()
        for component in (self.hands, self.voice, self.visualizer):
            try:
                component.stop()
            except Exception:
                LOGGER.exception("fullstack component failed during shutdown")
        self.controller.close()
        self.stopped = True
        self.started = False

    def run_window(self) -> None:
        """Create the native visualizer window on the foreground thread."""
        if os.environ.get("JARVIS_SMOKE", "0").strip().lower() in {"1", "true", "yes", "on"}:
            threading.Event().wait()
            return
        try:
            import webview
        except ImportError as exc:
            raise RuntimeError("pywebview is required for the native Jarvis window") from exc
        self._window = webview.create_window(
            "Jarvis",
            self.visualizer.url(),
            fullscreen=True,
            min_size=(800, 600),
        )
        webview.start(debug=False)


def main() -> int:
    visualizer = VisualizerAdapter()
    host: FullstackJarvisHost | None = None
    try:
        # Start the lightweight embedded visualizer before constructing the
        # heavier Jarvis controller. This guarantees that the presentation
        # surface is available immediately even when core/cloud initialization
        # takes time during first launch or after an update.
        visualizer.start()
        controller = JarvisDesktopController()
        host = FullstackJarvisHost(controller, visualizer=visualizer)
        host.start()
        host.run_window()
        return 0
    except Exception as exc:
        LOGGER.exception("Jarvis Fullstack host failed to start")
        if os.environ.get("JARVIS_SMOKE", "0").strip().lower() not in {"1", "true", "yes", "on"}:
            try:
                import tkinter.messagebox as messagebox
                messagebox.showerror("Jarvis", f"Jarvis could not start the Fullstack interface.\n\n{exc}")
            except Exception:
                pass
        return 1
    finally:
        if host is not None:
            host.stop()
        else:
            try:
                visualizer.stop()
            except Exception:
                LOGGER.exception("embedded visualizer failed during startup cleanup")


if __name__ == "__main__":
    raise SystemExit(main())
