"""Native Windows Fullstack Agent host for Jarvis.

The Jarvis runtime remains the only planner/tool executor. This host adds the
original Fullstack Agent presentation/voice layer without using its Claude
brain. The obsolete 640x118 Tk chat bar is intentionally gone.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from collections import deque
from typing import Any

from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.omniroute_setup import OmniRouteProvisioner
from quality_of_life.elevenlabs_voice import ElevenLabsMouth
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
FLOATING_HOTKEY_LABEL = "Ctrl+Alt+Shift+F12"
FLOATING_HOTKEY_ID = 0x4A52
FLOATING_POSITION_FILE = LOG_DIR.parent / "settings" / "floating_text_link.json"


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
    """Bridge Backtalk ears into Jarvis while using ElevenLabs as the sole TTS engine."""

    def __init__(self, controller: JarvisDesktopController) -> None:
        self.controller = controller
        self.bridge: Any | None = None
        self.elevenlabs = ElevenLabsMouth()
        self._transcript_lock = threading.RLock()
        self._transcript_queue: deque[str] = deque(maxlen=100)

    def _record_transcript(self, text: str) -> None:
        message = str(text or "").strip()
        if not message:
            return
        with self._transcript_lock:
            self._transcript_queue.append(message[:12000])

    def drain_transcript(self) -> list[str]:
        with self._transcript_lock:
            items = list(self._transcript_queue)
            self._transcript_queue.clear()
        return items

    @staticmethod
    def _truthy(name: str) -> bool:
        return os.environ.get(name, "0").strip().lower() in {"1", "true", "yes", "on"}

    def _smoke_validate_embedded_backtalk(self) -> None:
        vendor = embedded_path("backtalk/source")
        vendor_text = str(vendor)
        if vendor_text not in sys.path:
            sys.path.insert(0, vendor_text)
        from backtalk.ears import Ears
        from backtalk.mouth import Mouth
        from backtalk.ptt import PTTListener
        from quality_of_life.elevenlabs_voice import ElevenLabsClient, ElevenLabsMouth
        if not callable(getattr(ElevenLabsClient, "synthesize", None)):
            raise RuntimeError("ElevenLabs synthesis client is incomplete")
        LOGGER.info("embedded Backtalk + ElevenLabs voice modules validated: %s / %s", vendor, ElevenLabsMouth.__name__)

    def start(self) -> None:
        if self._truthy("JARVIS_SMOKE") and self._truthy("JARVIS_SMOKE_VOICE"):
            self._smoke_validate_embedded_backtalk()
            return
        if self._truthy("JARVIS_DISABLE_VOICE"):
            LOGGER.info("voice disabled by configuration")
            return
        from scripts.jarvis_voice_bridge import JarvisVoiceBridge
        self.bridge = JarvisVoiceBridge(
            self.controller,
            mouth=self.elevenlabs,
            on_output=self._record_transcript,
        )
        self.bridge.start()

    def stop(self) -> None:
        if self.bridge is not None:
            self.bridge.stop()
            self.bridge = None
        else:
            self.elevenlabs.shutdown()


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


class FloatingTextHotkey:
    """Register a dedicated system-wide hotkey for the floating Jarvis command bar."""

    MOD_CONTROL = 0x0002
    MOD_ALT = 0x0001
    MOD_SHIFT = 0x0004
    MOD_NOREPEAT = 0x4000
    VK_F12 = 0x7B
    WM_HOTKEY = 0x0312
    WM_QUIT = 0x0012

    def __init__(self, callback: callable) -> None:
        self.callback = callback
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.thread_id: int | None = None
        self.registered = False

    @property
    def enabled(self) -> bool:
        return sys.platform == "win32" and os.environ.get("JARVIS_SMOKE", "0").strip().lower() not in {"1", "true", "yes", "on"}

    def start(self) -> None:
        if not self.enabled or (self.thread and self.thread.is_alive()):
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, name="jarvis-floating-hotkey", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        thread_id = self.thread_id
        if thread_id is not None and sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.PostThreadMessageW(thread_id, self.WM_QUIT, 0, 0)
            except Exception:
                pass
        if self.thread is not None and self.thread.is_alive() and threading.current_thread() is not self.thread:
            self.thread.join(timeout=2)
        self.thread = None
        self.thread_id = None
        self.registered = False

    def _run(self) -> None:
        if not self.enabled:
            return
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self.thread_id = int(kernel32.GetCurrentThreadId())
        modifiers = self.MOD_CONTROL | self.MOD_ALT | self.MOD_SHIFT | self.MOD_NOREPEAT
        try:
            msg = wintypes.MSG()
            user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
            if not user32.RegisterHotKey(None, FLOATING_HOTKEY_ID, modifiers, self.VK_F12):
                LOGGER.warning("floating command bar hotkey %s could not be registered; it remains available from the UI", FLOATING_HOTKEY_LABEL)
                return
            self.registered = True
            LOGGER.info("floating command bar global hotkey registered: %s", FLOATING_HOTKEY_LABEL)
            while not self.stop_event.is_set():
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result in (-1, 0):
                    break
                if msg.message == self.WM_HOTKEY and int(msg.wParam) == FLOATING_HOTKEY_ID:
                    try:
                        self.callback()
                    except Exception:
                        LOGGER.exception("floating command bar hotkey callback failed")
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception:
            LOGGER.exception("floating command bar hotkey listener failed")
        finally:
            if self.registered:
                try:
                    user32.UnregisterHotKey(None, FLOATING_HOTKEY_ID)
                except Exception:
                    pass
            self.registered = False


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


class JarvisWebApi:
    """Small pywebview bridge for the centered Jarvis text input."""

    def __init__(self, host: "FullstackJarvisHost") -> None:
        self.host = host
        self._lock = threading.Lock()

    @staticmethod
    def _payload(result: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "text": str(getattr(result, "text", result)),
            "needs_confirmation": bool(getattr(result, "needs_confirmation", False)),
        }

    def toggle_text_link(self, detached: bool | None = None) -> dict[str, Any]:
        return self.host.toggle_text_link(detached)

    def text_link_state(self) -> dict[str, Any]:
        return self.host.text_link_state()

    def voice_transcript(self) -> dict[str, Any]:
        voice = getattr(self.host, "voice", None)
        drain = getattr(voice, "drain_transcript", None)
        if not callable(drain):
            return {"ok": True, "messages": []}
        try:
            return {"ok": True, "messages": [str(item)[:12000] for item in drain()]}
        except Exception:
            return {"ok": True, "messages": []}

    def voice_audio(self) -> dict[str, Any]:
        try:
            return self.host.voice_audio()
        except Exception:
            return {"ok": True, "items": []}

    def elevenlabs_status(self) -> dict[str, Any]:
        return self.host.elevenlabs_status()

    def elevenlabs_configure(self, api_key: str, voice_id: str = "", model_id: str = "") -> dict[str, Any]:
        return self.host.configure_elevenlabs(api_key, voice_id, model_id)

    def elevenlabs_test(self) -> dict[str, Any]:
        return self.host.test_elevenlabs()

    def elevenlabs_voices(self) -> dict[str, Any]:
        return self.host.elevenlabs_voices()

    def omniroute_detect_provider(self, api_key: str) -> dict[str, Any]:
        from quality_of_life.omniroute_setup import detect_provider_from_key
        provider = detect_provider_from_key(api_key)
        return {"ok": True, "provider": provider, "detected": bool(provider)}

    def open_omniroute_settings(self) -> dict[str, Any]:
        return self.host.open_omniroute_settings()

    def omniroute_status(self) -> dict[str, Any]:
        return self.host.omniroute_status()

    def omniroute_configure_provider(self, provider: str, api_key: str) -> dict[str, Any]:
        return self.host.configure_omniroute_provider(provider, api_key)

    def omniroute_test_provider(self, provider: str) -> dict[str, Any]:
        return self.host.test_omniroute_provider(provider)

    def open_omniroute_dashboard(self) -> dict[str, Any]:
        return self.host.open_omniroute_dashboard()

    def submit_text(self, text: str, confirmed: bool = False) -> dict[str, Any]:
        normalized = str(text or "").strip()
        if not normalized:
            return {"ok": False, "error": "Enter a request first.", "needs_confirmation": False}
        with self._lock:
            try:
                bridge = getattr(self.host.voice, "bridge", None)
                if bridge is not None and not confirmed:
                    result = bridge.handle_transcript(normalized)
                else:
                    result = self.host.controller.execute_request(normalized, confirmed=bool(confirmed))
                return self._payload(result)
            except Exception as exc:
                LOGGER.exception("center text input request failed")
                message = f"{type(exc).__name__}: {exc}".replace("OPENAI_API_KEY", "[secret]")
                return {"ok": False, "error": message[:500], "needs_confirmation": False}


TEXT_INPUT_SCRIPT = r'''
(function () {
  "use strict";
  if (window.__jarvisTextInputInstalled) return;
  window.__jarvisTextInputInstalled = true;

  const style = document.createElement("style");
  style.id = "jarvis-text-input-style";
  style.textContent = `
    #jarvis-text-shell{position:fixed;z-index:2147483647;left:24px;top:24px;width:min(760px,calc(100vw - 48px));height:min(420px,calc(100vh - 48px));min-width:320px;min-height:170px;max-width:calc(100vw - 16px);max-height:calc(100vh - 16px);box-sizing:border-box;padding:12px;border:1px solid var(--jarvis-text-accent,rgba(91,190,255,.34));border-radius:16px;background:radial-gradient(circle at 15% 5%,rgba(78,196,255,.10),transparent 35%),linear-gradient(145deg,rgba(2,14,28,.94),rgba(1,6,13,.92));box-shadow:0 24px 78px rgba(0,0,0,.52),0 0 46px var(--jarvis-text-glow,rgba(35,150,238,.20)),inset 0 0 34px rgba(56,179,247,.045);backdrop-filter:blur(15px);overflow:hidden;resize:both;pointer-events:auto;color:#e8f5fb;font-family:var(--mono,Consolas,monospace);opacity:.96}
    #jarvis-text-shell:hover,#jarvis-text-shell.jarvis-active{opacity:1;box-shadow:0 28px 96px rgba(0,0,0,.58),0 0 58px var(--jarvis-text-glow,rgba(35,150,238,.28)),inset 0 0 36px rgba(56,179,247,.06)}
    #jarvis-text-header{height:28px;display:flex;align-items:center;gap:9px;cursor:move;user-select:none}
    #jarvis-text-dot{width:8px;height:8px;border-radius:50%;background:#83ddff;box-shadow:0 0 14px rgba(131,221,255,.86);flex:0 0 auto}
    #jarvis-text-label{font-size:9px;letter-spacing:.28em;color:var(--jarvis-text-label-color,#c6efff);white-space:nowrap}
    #jarvis-text-build{font-size:7px;letter-spacing:.11em;color:#5c86a2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    #jarvis-text-actions{margin-left:auto;display:flex;gap:5px}
    .jarvis-text-btn{width:28px;height:24px;border:1px solid rgba(111,199,242,.18);border-radius:7px;background:rgba(4,18,32,.60);color:#86c9eb;cursor:pointer;font:9px var(--mono,Consolas,monospace)}
    .jarvis-text-btn:hover{border-color:rgba(152,231,255,.65);color:#ecfbff}
    #jarvis-text-history{height:calc(100% - 100px);min-height:48px;overflow:auto;padding:7px 3px 5px;display:flex;flex-direction:column;gap:7px;scrollbar-width:thin;scroll-behavior:smooth}
    .jarvis-text-message{max-width:94%;padding:8px 10px;border:1px solid rgba(111,199,242,.10);border-radius:9px;background:rgba(255,255,255,.018);font-size:10px;line-height:1.55;white-space:pre-wrap;word-break:break-word;color:#84aec7}
    .jarvis-text-message.user{align-self:flex-end;border-color:rgba(85,194,255,.21);background:rgba(25,117,176,.09);color:#cbf0ff}
    .jarvis-text-message.jarvis{align-self:flex-start;border-color:rgba(100,211,255,.15);color:#e0f6ff;background:rgba(20,96,144,.055)}
    .jarvis-text-message.error{align-self:flex-start;border-color:rgba(255,120,145,.22);color:#ff9dad;background:rgba(150,35,55,.06)}
    #jarvis-text-row{display:flex;gap:8px;align-items:flex-end;padding-top:7px}
    #jarvis-text-input{min-width:0;min-height:42px;max-height:130px;flex:1;resize:none;overflow:auto;border:1px solid rgba(111,199,242,.20);outline:none;border-radius:10px;padding:11px 12px;box-sizing:border-box;color:#e9f7fd;background:rgba(0,0,0,.28);font:11px/1.4 var(--mono,Consolas,monospace);caret-color:#8be2ff}
    #jarvis-text-input:focus{border-color:rgba(151,230,255,.66);box-shadow:0 0 20px rgba(50,165,239,.12)}
    #jarvis-text-input::placeholder{color:#60809a}
    #jarvis-text-float,#jarvis-text-send{flex:0 0 auto;width:42px;height:42px;border:1px solid rgba(111,199,242,.21);border-radius:10px;background:rgba(5,24,39,.64);color:#c7edff;cursor:pointer;font:15px var(--mono,Consolas,monospace)}
    #jarvis-text-float:hover,#jarvis-text-send:hover{border-color:rgba(151,230,255,.68);background:rgba(27,124,184,.15)}
    #jarvis-text-status{height:16px;margin-top:5px;font-size:8px;line-height:1.4;letter-spacing:.10em;color:#668ba5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    #jarvis-text-status.jarvis-error{color:#ff8fa8}
    #jarvis-text-hint{font-size:7px;letter-spacing:.12em;color:#466a82;user-select:none}
    #jarvis-text-shell.history-collapsed{height:48px!important;min-height:48px!important;resize:none}
    #jarvis-text-shell.history-collapsed #jarvis-text-history,#jarvis-text-shell.history-collapsed #jarvis-text-row,#jarvis-text-shell.history-collapsed #jarvis-text-status,#jarvis-text-shell.history-collapsed #jarvis-text-hint{display:none}
    #jarvis-text-shell[data-theme="neural"]{--jarvis-text-accent:rgba(76,199,255,.46);--jarvis-text-glow:rgba(39,151,239,.26);--jarvis-text-label-color:#d0f3ff}
    #jarvis-text-shell[data-theme="classic"]{--jarvis-text-accent:rgba(123,218,177,.40);--jarvis-text-glow:rgba(44,177,127,.18);--jarvis-text-label-color:#d4f5e4}
  `;
  document.head.appendChild(style);

  const shell = document.createElement("div");
  shell.id = "jarvis-text-shell";
  shell.innerHTML = `
    <div id="jarvis-text-header"><span id="jarvis-text-dot"></span><span id="jarvis-text-label">JARVIS COMMAND</span><span id="jarvis-text-build"></span><span id="jarvis-text-actions"><button class="jarvis-text-btn" id="jarvis-text-settings" type="button" title="Open AI provider settings">⚙</button><button class="jarvis-text-btn" id="jarvis-text-min" type="button" title="Collapse command transcript">—</button><button class="jarvis-text-btn" id="jarvis-text-float" type="button" title="Detach command surface">↗</button></span></div>
    <div id="jarvis-text-history" aria-live="polite"><div class="jarvis-text-message jarvis">Command surface online. Jarvis responses will remain visible here.</div></div>
    <div id="jarvis-text-row"><textarea id="jarvis-text-input" rows="1" autocomplete="off" spellcheck="false" placeholder="Talk to Jarvis…" aria-label="Talk to Jarvis by text" disabled></textarea><button id="jarvis-text-send" type="button" aria-label="Send text to Jarvis" disabled>↵</button></div>
    <div id="jarvis-text-status"></div>
    <div id="jarvis-text-hint">ENTER — SEND · SHIFT+ENTER — NEW LINE · DRAG HEADER — MOVE · RESIZE CORNER — ANY SIZE</div>
  `;
  document.body.appendChild(shell);

  const input = shell.querySelector("#jarvis-text-input");
  const floatButton = shell.querySelector("#jarvis-text-float");
  const send = shell.querySelector("#jarvis-text-send");
  const status = shell.querySelector("#jarvis-text-status");
  const history = shell.querySelector("#jarvis-text-history");
  const buildLabel = shell.querySelector("#jarvis-text-build");
  const minButton = shell.querySelector("#jarvis-text-min");
  const settingsButton = shell.querySelector("#jarvis-text-settings");
  const header = shell.querySelector("#jarvis-text-header");
  let apiReady = false;
  let historyCollapsed = false;
  let dragState = null;

  function persistGeometry(){
    if(historyCollapsed)return;
    try{
      const rect=shell.getBoundingClientRect();
      localStorage.setItem("jarvis.textSurface.geometry",JSON.stringify({x:Math.round(rect.left),y:Math.round(rect.top),width:Math.round(rect.width),height:Math.round(rect.height)}));
    }catch(_){}
  }
  function restoreGeometry(){
    try{
      const g=JSON.parse(localStorage.getItem("jarvis.textSurface.geometry")||"null");
      if(g&&Number.isFinite(g.x)&&Number.isFinite(g.y)&&Number.isFinite(g.width)&&Number.isFinite(g.height)){
        shell.style.width=Math.max(320,Math.min(window.innerWidth-16,g.width))+"px";
        shell.style.height=Math.max(170,Math.min(window.innerHeight-16,g.height))+"px";
        shell.style.left=Math.max(8,Math.min(window.innerWidth-shell.offsetWidth-8,g.x))+"px";
        shell.style.top=Math.max(8,Math.min(window.innerHeight-shell.offsetHeight-8,g.y))+"px";
        return;
      }
    }catch(_){}
    shell.style.left=Math.max(8,Math.round((window.innerWidth-shell.offsetWidth)/2))+"px";
    shell.style.top=Math.max(8,Math.round((window.innerHeight-shell.offsetHeight)/2))+"px";
  }
  let lastTranscriptKey = "";
  let lastTranscriptAt = 0;
  function addMessage(kind,text){
    const value=String(text||"").slice(0,12000);
    if(!value)return;
    const key=(kind||"jarvis")+"|"+value;
    const now=Date.now();
    if(key===lastTranscriptKey && now-lastTranscriptAt<1400)return;
    lastTranscriptKey=key;lastTranscriptAt=now;
    const row=document.createElement("div");
    row.className="jarvis-text-message "+(kind==="user"?"user":kind==="error"?"error":"jarvis");
    row.textContent=value;
    history.appendChild(row);
    while(history.children.length>100)history.removeChild(history.firstChild);
    if(!historyCollapsed)history.scrollTop=history.scrollHeight;
  }
  function setTheme(id,name,version){
    const key=String(id||"").toLowerCase().includes("neural")?"neural":"classic";
    shell.dataset.theme=key;
    buildLabel.textContent=(name||id||"JARVIS")+" · v"+String(version||"");
  }
  function setCollapsed(collapsed){
    historyCollapsed=!!collapsed;
    shell.classList.toggle("history-collapsed",historyCollapsed);
    minButton.textContent=historyCollapsed?"+":"—";
    if(!historyCollapsed)window.setTimeout(()=>history.scrollTop=history.scrollHeight,0);
    try{localStorage.setItem("jarvis.textSurface.collapsed",historyCollapsed?"1":"0");}catch(_){}
  }
  function startDrag(event){
    if(event.button!==undefined&&event.button!==0)return;
    dragState={x:event.clientX,y:event.clientY,left:parseFloat(shell.style.left)||0,top:parseFloat(shell.style.top)||0};
    try{header.setPointerCapture(event.pointerId);}catch(_){}
  }
  function moveDrag(event){
    if(!dragState)return;
    const dx=event.clientX-dragState.x,dy=event.clientY-dragState.y;
    shell.style.left=Math.max(8,Math.min(window.innerWidth-shell.offsetWidth-8,dragState.left+dx))+"px";
    shell.style.top=Math.max(8,Math.min(window.innerHeight-shell.offsetHeight-8,dragState.top+dy))+"px";
  }
  function stopDrag(){if(dragState){dragState=null;persistGeometry();}}

  async function submit(confirmed){
    const textValue=input.value.trim();
    if(!textValue||!apiReady)return;
    setActive(true);
    addMessage("user",textValue);
    input.disabled=true;send.disabled=true;
    status.classList.remove("jarvis-error");status.textContent="PROCESSING · JARVIS LINK ACTIVE";
    try{
      let result=await window.pywebview.api.submit_text(textValue,!!confirmed);
      if(result&&result.needs_confirmation&&!confirmed){
        addMessage("jarvis",result.text||"Confirmation required.");
        status.textContent="AWAITING CONFIRMATION";
        const accepted=window.confirm(result.text||"Jarvis requires confirmation for this action.");
        if(accepted)result=await window.pywebview.api.submit_text(textValue,true);
        else{addMessage("jarvis","Command cancelled.");status.textContent="CANCELLED";result=null;}
      }
      if(result){
        if(result.ok){
          const response=result.text||"DONE";
          addMessage("jarvis",response);
          status.textContent="RESPONSE RECEIVED · "+response.replace(/\s+/g," ").slice(0,90);
          input.value="";
        }else{
          const error=result.error||"Jarvis request failed.";
          addMessage("error",error);status.classList.add("jarvis-error");status.textContent=error.slice(0,180);
        }
      }
    }catch(error){
      const message="TEXT LINK ERROR: "+String(error);
      addMessage("error",message);status.classList.add("jarvis-error");status.textContent=message.slice(0,180);
    }finally{
      input.disabled=false;send.disabled=false;input.focus();persistGeometry();
    }
  }

  function setActive(active){
    if(active)shell.classList.add("jarvis-active");
    else if(document.activeElement!==input)shell.classList.remove("jarvis-active");
  }

  shell.addEventListener("mouseenter",()=>setActive(true));
  shell.addEventListener("mouseleave",()=>setActive(false));
  shell.addEventListener("focusin",()=>setActive(true));
  shell.addEventListener("focusout",()=>window.setTimeout(()=>setActive(false),0));
  input.addEventListener("keydown",event=>{
    if(event.key==="Enter"&&!event.shiftKey){event.preventDefault();submit(false);}
    else if(event.key==="Escape"){event.preventDefault();input.value="";status.textContent="";input.blur();}
  });
  send.addEventListener("click",()=>submit(false));
  minButton.addEventListener("click",()=>setCollapsed(!historyCollapsed));
  settingsButton.addEventListener("click",async()=>{
    if(!apiReady||!window.pywebview.api.open_omniroute_settings)return;
    try{await window.pywebview.api.open_omniroute_settings();}
    catch(error){const message="AI PROVIDER SETTINGS ERROR: "+String(error);addMessage("error",message);status.classList.add("jarvis-error");status.textContent=message.slice(0,180);}
  });
  header.addEventListener("pointerdown",startDrag);
  header.addEventListener("pointermove",moveDrag);
  header.addEventListener("pointerup",stopDrag);
  header.addEventListener("pointercancel",stopDrag);
  shell.addEventListener("mouseup",persistGeometry);
  floatButton.addEventListener("click",async()=>{
    if(!apiReady||!window.pywebview.api.toggle_text_link)return;
    try{await window.pywebview.api.toggle_text_link(true);shell.style.display="none";}
    catch(error){const message="FLOAT LINK ERROR: "+String(error);addMessage("error",message);status.classList.add("jarvis-error");status.textContent=message;}
  });
  window.addEventListener("resize",()=>{
    const rect=shell.getBoundingClientRect();
    shell.style.left=Math.max(8,Math.min(window.innerWidth-rect.width-8,rect.left))+"px";
    shell.style.top=Math.max(8,Math.min(window.innerHeight-rect.height-8,rect.top))+"px";
    persistGeometry();
  });

  function markReady(){
    apiReady=!!(window.pywebview&&window.pywebview.api);
    input.disabled=!apiReady;floatButton.disabled=!apiReady;send.disabled=!apiReady;
    if(apiReady)status.textContent="READY — TEXT LINK ONLINE";
  }
  restoreGeometry();
  try{historyCollapsed=localStorage.getItem("jarvis.textSurface.collapsed")==="1";}catch(_){}
  setCollapsed(historyCollapsed);
  setTheme("default","JARVIS","unified");

  window.addEventListener("pywebviewready",markReady);
  const readyPoll=window.setInterval(function(){
    if(window.pywebview&&window.pywebview.api){
      markReady();
      window.clearInterval(readyPoll);
    }
  },250);
  if(window.pywebview&&window.pywebview.api)markReady();

  async function pollVoiceTranscript(){
    if(!apiReady||!window.pywebview.api.voice_transcript)return;
    try{const result=await window.pywebview.api.voice_transcript();if(result&&Array.isArray(result.messages))result.messages.forEach(function(message){addMessage("jarvis",message);});}catch(_){}
  }
  setInterval(pollVoiceTranscript,700);
  pollVoiceTranscript();

  window.jarvisTextInput={
    setVisible:function(visible){shell.style.display=visible?"":"none";if(!visible)setActive(false);},
    focus:function(){if(apiReady)input.focus();},
    setBuildTheme:function(id,name,version){setTheme(id,name,version);},
    appendOutput:function(text){addMessage("jarvis",text);},
    geometry:function(){const rect=shell.getBoundingClientRect();return{x:rect.left,y:rect.top,width:rect.width,height:rect.height};}
  };
})();
'''



FLOATING_TEXT_INPUT_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jarvis Neural Floating Command</title>
<style>
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#020914;color:#e6f7ff;font-family:Consolas,"SFMono-Regular",monospace}#frame{width:100%;height:100%;padding:10px;border:1px solid rgba(79,188,255,.28);border-radius:16px;background:linear-gradient(145deg,rgba(5,17,12,.98),rgba(2,7,5,.96));box-shadow:0 12px 36px rgba(0,0,0,.5),inset 0 0 24px rgba(35,133,205,.05)}#bar{display:flex;align-items:center;gap:9px;margin-bottom:8px;cursor:move;user-select:none}.pywebview-drag-region{cursor:move}.dot{width:7px;height:7px;border-radius:50%;background:#4dc7ff;box-shadow:0 0 11px rgba(77,199,255,.78)}#title{flex:1;font-size:9px;letter-spacing:.22em;color:#9edbff}#hotkey{font-size:7px;letter-spacing:.09em;color:#5d7891}#close{width:24px;height:22px;border:1px solid rgba(255,255,255,.08);border-radius:6px;background:transparent;color:#789087;cursor:pointer;font:inherit}#close:hover{border-color:rgba(255,140,152,.38);color:#ff9aa5}#row{display:flex;gap:8px;align-items:center}#input{min-width:0;flex:1;height:42px;border:1px solid rgba(91,190,255,.28);border-radius:9px;outline:none;padding:0 13px;background:rgba(0,0,0,.28);color:#e8f0f2;font:inherit;font-size:13px;letter-spacing:.03em;caret-color:#7edcff}#input:focus{border-color:rgba(91,190,255,.72);box-shadow:0 0 18px rgba(41,151,224,.14)}#input::placeholder{color:#627d95}#send{width:44px;height:42px;border:1px solid rgba(91,190,255,.30);border-radius:9px;background:rgba(61,220,132,.07);color:#b9e9ff;cursor:pointer;font:inherit;font-size:17px}#send:hover{background:rgba(61,220,132,.15);border-color:rgba(143,232,184,.7)}#status{margin-top:7px;min-height:12px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;color:#799bb7;font-size:8px;letter-spacing:.09em}#status.error{color:#ff8fa8}</style>
</head>
<body><div id="frame"><div id="bar" class="pywebview-drag-region"><span class="dot"></span><span id="title">JARVIS NEURAL FLOATING LINK</span><span id="hotkey">CTRL+ALT+SHIFT+F12</span><button id="close" type="button" aria-label="Return Jarvis text link to the main app">×</button></div><div id="row"><input id="input" type="text" autocomplete="off" spellcheck="false" placeholder="Talk to Jarvis from anywhere on your desktop…" disabled><button id="send" type="button" aria-label="Send text to Jarvis" disabled>↵</button></div><div id="status">CONNECTING…</div></div>
<script>(function(){const input=document.getElementById("input"),send=document.getElementById("send"),close=document.getElementById("close"),status=document.getElementById("status");let ready=false;async function submit(confirmed){const text=input.value.trim();if(!text||!ready)return;input.disabled=true;send.disabled=true;status.classList.remove("error");status.textContent="PROCESSING…";try{let r=await window.pywebview.api.submit_text(text,!!confirmed);if(r&&r.needs_confirmation&&!confirmed){const ok=window.confirm(r.text||"Jarvis requires confirmation for this action.");if(ok)r=await window.pywebview.api.submit_text(text,true);else{status.textContent="CANCELLED";r=null}}if(r){if(r.ok){status.textContent=r.text||"DONE";input.value=""}else{status.classList.add("error");status.textContent=r.error||"Jarvis request failed."}}}catch(e){status.classList.add("error");status.textContent="TEXT LINK ERROR: "+String(e)}finally{input.disabled=false;send.disabled=false;input.focus()}}input.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();submit(false)}else if(e.key==="Escape"){e.preventDefault();input.value="";status.textContent="";input.blur()}});send.addEventListener("click",()=>submit(false));close.addEventListener("click",()=>{if(window.pywebview&&window.pywebview.api)window.pywebview.api.toggle_text_link(false)});function readyFn(){ready=!!(window.pywebview&&window.pywebview.api);input.disabled=!ready;send.disabled=!ready;if(ready){status.textContent="FLOATING TEXT LINK ONLINE";setTimeout(()=>input.focus(),80)}}window.addEventListener("pywebviewready",readyFn);const readyPoll=window.setInterval(function(){if(window.pywebview&&window.pywebview.api){readyFn();window.clearInterval(readyPoll)}} ,250);if(window.pywebview&&window.pywebview.api)readyFn()})();  const jarvisVoicePlayer=(function(){
    let current=null,lastSequence=0,pending=[],polling=false;
    function stopCurrent(){if(current){try{current.pause();current.currentTime=0;}catch(_e){}current=null;}}
    function playNext(){
      if(current||!pending.length)return;
      const packet=pending.shift();
      if(!packet||!packet.data){playNext();return;}
      const audio=new Audio("data:"+(packet.mime||"audio/mpeg")+";base64,"+packet.data);
      current=audio;
      audio.onended=()=>{current=null;playNext();};
      audio.onerror=()=>{current=null;playNext();};
      audio.play().catch(()=>{pending.unshift(packet);current=null;});
    }
    function enqueue(items){
      if(!Array.isArray(items))return;
      for(const item of items){
        const seq=Number(item&&item.sequence||0);
        if(!seq||seq<lastSequence)continue;
        if(seq>lastSequence){lastSequence=seq;pending=[];stopCurrent();}
        if(seq===lastSequence&&item&&item.data)pending.push(item);
      }
      playNext();
    }
    async function poll(){
      if(polling||!(window.pywebview&&window.pywebview.api))return;
      polling=true;
      try{const result=await window.pywebview.api.voice_audio();enqueue(result&&result.items);}
      catch(_e){}finally{polling=false;}
    }
    function resume(){playNext();}
    document.addEventListener("pointerdown",resume,{passive:true});
    window.jarvisVoicePlayer={enqueue,poll,resume};
    window.setInterval(poll,180);
    poll();
    return window.jarvisVoicePlayer;
  })();
</script>
</body></html>'''

OMNIROUTE_SETTINGS_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jarvis AI Providers</title>
<style>.voice-choice{height:30px;margin:3px 0;padding:0 10px;width:100%;text-align:left}.voice-choice{font-size:8px}
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;background:#020914;color:#dff5ff;font-family:Consolas,"SFMono-Regular",monospace}
body{padding:18px}.panel{height:100%;display:flex;flex-direction:column;gap:12px;border:1px solid rgba(91,190,255,.25);border-radius:18px;padding:18px;background:radial-gradient(circle at 15% 5%,rgba(78,196,255,.10),transparent 35%),linear-gradient(145deg,rgba(3,17,30,.98),rgba(1,7,13,.98));box-shadow:0 20px 70px rgba(0,0,0,.52),inset 0 0 38px rgba(56,179,247,.04)}
h1{font-size:13px;letter-spacing:.20em;margin:0;color:#dff6ff}.sub{font-size:8px;line-height:1.6;color:#67879d}.status{padding:9px;border:1px solid rgba(111,199,242,.14);border-radius:10px;background:rgba(255,255,255,.018);font-size:9px;line-height:1.5}.row{display:flex;gap:8px}.field{display:flex;flex-direction:column;gap:5px;flex:1}.field label{font-size:8px;letter-spacing:.12em;color:#7698ad}select,input{width:100%;height:38px;border:1px solid rgba(111,199,242,.20);border-radius:8px;background:rgba(0,0,0,.25);color:#e8f7ff;outline:none;padding:0 10px;font:10px Consolas,"SFMono-Regular",monospace}input:focus,select:focus{border-color:rgba(151,230,255,.66);box-shadow:0 0 18px rgba(50,165,239,.12)}button{height:36px;border:1px solid rgba(111,199,242,.21);border-radius:8px;background:rgba(5,24,39,.64);color:#c7edff;cursor:pointer;font:9px Consolas,"SFMono-Regular",monospace;padding:0 13px}button:hover{border-color:rgba(151,230,255,.68);background:rgba(27,124,184,.15)}.primary{background:rgba(33,131,180,.14);border-color:rgba(106,211,255,.30)}.providers{display:flex;flex-direction:column;gap:6px;min-height:70px;overflow:auto}.provider{display:flex;justify-content:space-between;gap:10px;padding:8px;border-radius:8px;background:rgba(255,255,255,.02);border:1px solid rgba(111,199,242,.09);font-size:9px}.muted{color:#628299}.ok{color:#9ceac0}.bad{color:#ff9cab}.actions{display:flex;gap:7px;flex-wrap:wrap}
</style>
</head>
<body><div class="panel">
<h1>JARVIS · AI PROVIDERS</h1>
<div class="sub">OmniRoute is built into the Jarvis release. Paste an API key and Jarvis safely auto-detects recognizable provider formats; ambiguous keys require an explicit provider selection.</div>
<div class="status" id="runtime">Checking OmniRoute runtime…</div>
<div><div class="field"><label>PROVIDER</label><select id="provider"><option value="auto" selected>Auto-detect from API key</option><option value="openai">OpenAI</option><option value="anthropic">Anthropic</option><option value="gemini">Google AI</option><option value="openrouter">OpenRouter</option><option value="deepseek">DeepSeek</option><option value="groq">Groq</option><option value="xai">xAI</option><option value="mistral">Mistral</option><option value="cerebras">Cerebras</option><option value="together">Together</option><option value="fireworks">Fireworks</option><option value="custom">Custom provider ID…</option></select></div></div>
<div class="field" id="customWrap" style="display:none"><label>CUSTOM PROVIDER ID</label><input id="customProvider" autocomplete="off" placeholder="provider-id"></div>
<div class="field"><label>API KEY</label><input id="key" type="password" autocomplete="new-password" placeholder="Paste provider API key"></div>
<div class="actions"><button id="connect" class="primary" type="button">CONNECT & TEST</button><button id="refresh" type="button">REFRESH</button><button id="dashboard" type="button">OPEN DASHBOARD</button></div>
<div class="sub" id="message">Provider secrets are sent directly to OmniRoute over a local process boundary.</div>
<div><div class="sub" style="margin-bottom:6px">CONFIGURED PROVIDERS</div><div class="providers" id="providers"><div class="muted">No provider status yet.</div></div></div>
<div style="border-top:1px solid rgba(111,199,242,.10);padding-top:12px">
<div class="sub" style="margin-bottom:6px">VOICE ENGINE · ELEVENLABS</div>
<div class="status" id="voiceRuntime">Checking ElevenLabs voice engine…</div>
<div class="field"><label>ELEVENLABS API KEY</label><input id="elevenKey" type="password" autocomplete="new-password" placeholder="Paste your ElevenLabs API key once"></div>
<div class="row">
<div class="field"><label>VOICE ID (OPTIONAL)</label><input id="voiceId" autocomplete="off" placeholder="Leave blank for configured/default voice"></div>
<div class="field"><label>MODEL</label><select id="voiceModel"><option value="eleven_v3_conversational">v3 Conversational · expressive JARVIS mode</option><option value="eleven_flash_v2_5">Flash v2.5 · low latency</option><option value="eleven_v3">v3 · maximum expressiveness</option></select></div>
</div>
<div class="actions"><button id="voiceSave" class="primary" type="button">SAVE & TEST VOICE</button><button id="voiceTest" type="button">TEST VOICE</button><button id="voiceLoad" type="button">LOAD VOICES</button></div>
<div class="sub" id="voiceMessage">The key is stored in the OS credential store and is never shown back here.</div>
<div class="providers" id="voiceList"><div class="muted">Available ElevenLabs voices appear here after connection.</div></div>
</div>
</div>
<script>
(function(){
"use strict";
const provider=document.getElementById("provider"), custom=document.getElementById("customWrap"), customInput=document.getElementById("customProvider"), key=document.getElementById("key"), connect=document.getElementById("connect"), refresh=document.getElementById("refresh"), dashboard=document.getElementById("dashboard"), runtime=document.getElementById("runtime"), message=document.getElementById("message"), providers=document.getElementById("providers");
const elevenKey=document.getElementById("elevenKey"), voiceId=document.getElementById("voiceId"), voiceModel=document.getElementById("voiceModel"), voiceSave=document.getElementById("voiceSave"), voiceTest=document.getElementById("voiceTest"), voiceLoad=document.getElementById("voiceLoad"), voiceRuntime=document.getElementById("voiceRuntime"), voiceMessage=document.getElementById("voiceMessage"), voiceList=document.getElementById("voiceList");
provider.addEventListener("change",()=>{custom.style.display=provider.value==="custom"?"":"none";});async function detectProvider(){
  if(provider.value!=="auto")return;
  const secret=key.value;
  if(!secret||!window.pywebview||!window.pywebview.api)return;
  try{
    const result=await window.pywebview.api.omniroute_detect_provider(secret);
    if(result&&result.provider){
      provider.value=result.provider;
      message.textContent="Detected provider: "+result.provider+". Click CONNECT & TEST.";
    }else{
      provider.value="auto";
      message.textContent="Provider format is ambiguous; choose the provider explicitly.";
    }
  }catch(_e){}
}
key.addEventListener("blur",detectProvider);
function render(data){
  if(!data){runtime.textContent="OmniRoute status unavailable.";return;}
  const version=data.version||"unknown", source=data.source||"unknown", ready=data.ready?"ONLINE":"STARTING";
  runtime.textContent="OMNIROUTE "+ready+" · v"+version+" · "+source+" · "+(data.base_url||"");
  const items=Array.isArray(data.providers)?data.providers:[];
  providers.innerHTML=items.length?items.map(item=>'<div class="provider"><span>'+String(item.name).replace(/[<>&]/g,"")+'</span><span class="'+(String(item.status||"").toLowerCase().includes("fail")?"bad":"ok")+'">'+String(item.status||"configured").replace(/[<>&]/g,"")+'</span></div>').join(""):'<div class="muted">No providers configured yet.</div>';
}
async function load(){
  try{const data=await window.pywebview.api.omniroute_status();render(data);}
  catch(e){runtime.textContent="STATUS ERROR";message.textContent=String(e);}
}
connect.addEventListener("click",async()=>{
  const secret=key.value;
  if(!secret){message.textContent="Enter an API key first.";return;}
  let selected=provider.value==="custom"?customInput.value.trim():provider.value;
  if(provider.value==="auto"){
    const detected=await window.pywebview.api.omniroute_detect_provider(secret);
    selected=detected&&detected.provider?detected.provider:"auto";
    if(selected==="auto"){message.textContent="Choose the provider for this key; its format is ambiguous.";return;}
    provider.value=selected;
  }
  if(!selected){message.textContent="Select a provider and enter its API key.";return;}
  connect.disabled=true;message.textContent="Connecting provider through OmniRoute…";
  try{
    const result=await window.pywebview.api.omniroute_configure_provider(selected,secret);
    key.value="";
    if(result&&result.tested===false){message.textContent="Credential saved; provider test could not complete."}
    else message.textContent=result&&result.message?result.message:"Provider connected and tested.";
    await load();
  }catch(e){key.value="";message.textContent="Provider setup failed without exposing the credential.";runtime.className="status bad";}
  finally{connect.disabled=false;}
});
refresh.addEventListener("click",load);
dashboard.addEventListener("click",async()=>{try{await window.pywebview.api.open_omniroute_dashboard();}catch(e){message.textContent="Dashboard could not be opened.";}});
async function loadVoice(){
  try{
    const data=await window.pywebview.api.elevenlabs_status();
    voiceRuntime.textContent=(data.configured?"ELEVENLABS READY":"ELEVENLABS KEY NEEDED")+" · "+(data.model_id||"");
    if(!voiceId.value&&data.voice_id)voiceId.value=data.voice_id;
    if(data.model_id)voiceModel.value=data.model_id;
    voiceMessage.textContent=data.last_error||"ElevenLabs voice path is ready.";
  }catch(_e){voiceRuntime.textContent="ELEVENLABS STATUS ERROR";}
}
async function saveVoice(){
  const secret=elevenKey.value;
  if(!secret){voiceMessage.textContent="Paste your ElevenLabs API key.";return;}
  voiceSave.disabled=true;voiceMessage.textContent="Saving securely and testing…";
  try{
    const result=await window.pywebview.api.elevenlabs_configure(secret,voiceId.value.trim(),voiceModel.value);
    elevenKey.value="";
    voiceMessage.textContent=result&&result.message?result.message:"ElevenLabs connected.";
    await loadVoice();
  }catch(_e){elevenKey.value="";voiceMessage.textContent="Voice setup failed without exposing the credential.";}
  finally{voiceSave.disabled=false;}
}
async function testVoice(){
  voiceTest.disabled=true;voiceMessage.textContent="Testing ElevenLabs…";
  try{
    const result=await window.pywebview.api.elevenlabs_test();
    voiceMessage.textContent=result&&result.message?result.message:"Voice test complete.";
  }catch(_e){voiceMessage.textContent="Voice test failed.";}
  finally{voiceTest.disabled=false;}
}
async function loadVoices(){
  voiceLoad.disabled=true;voiceMessage.textContent="Loading available voices…";
  try{
    const result=await window.pywebview.api.elevenlabs_voices();
    const items=Array.isArray(result&&result.voices)?result.voices:[];
    voiceList.innerHTML=items.length?items.slice(0,80).map(v=>'<button type="button" class="voice-choice" data-id="'+String(v.id).replace(/["<>&]/g,"")+'">'+String(v.name).replace(/[<>&]/g,"")+'</button>').join(""):'<div class="muted">No voices returned.</div>';
    voiceList.querySelectorAll(".voice-choice").forEach(btn=>btn.addEventListener("click",()=>{voiceId.value=btn.dataset.id||"";voiceMessage.textContent="Voice selected. Save & Test Voice to apply it.";}));
  }catch(_e){voiceMessage.textContent="Voice list could not be loaded.";}
  finally{voiceLoad.disabled=false;}
}

function ready(){if(window.pywebview&&window.pywebview.api){load();loadVoice();}}
window.addEventListener("pywebviewready",ready);
const poll=window.setInterval(()=>{if(window.pywebview&&window.pywebview.api){window.clearInterval(poll);load();}},250);
})();
</script>
</body></html>'''

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
        self._floating_window: Any | None = None
        self._floating_visible = False
        self._omniroute_settings_window: Any | None = None
        self.omniroute = OmniRouteProvisioner()
        self._floating_lock = threading.RLock()
        self._shutting_down = False
        self._web_api = JarvisWebApi(self)
        self._update_stop = threading.Event()
        self.updater = AutoUpdateController(self._update_stop, self._exit_for_update)
        self.floating_hotkey = FloatingTextHotkey(self._toggle_text_link_from_hotkey)
        self._omniroute_warmup_thread: threading.Thread | None = None

    @property
    def web_api(self) -> JarvisWebApi:
        return self._web_api

    def omniroute_status(self) -> dict[str, Any]:
        status = self.omniroute.status().as_dict()
        try:
            status["ready"] = bool(self.omniroute.probe_only())
        except Exception:
            status["ready"] = False
        try:
            status["providers"] = self.omniroute.list_providers(install_if_missing=False)
        except Exception:
            status["providers"] = []
        return status

    def configure_omniroute_provider(self, provider: str, api_key: str) -> dict[str, Any]:
        if not self.omniroute.ensure_running(wait_seconds=15):
            raise RuntimeError("OmniRoute did not become ready; provider credential was not submitted")
        result = self.omniroute.configure_provider(provider, api_key)
        test = self.omniroute.test_provider(provider)
        result["tested"] = bool(test.get("ok"))
        result["message"] = "Provider connected and tested" if result["tested"] else "Credential saved but provider test failed"
        return result

    def test_omniroute_provider(self, provider: str) -> dict[str, Any]:
        if not self.omniroute.ensure_running(wait_seconds=15):
            raise RuntimeError("OmniRoute did not become ready")
        return self.omniroute.test_provider(provider)

    def voice_audio(self) -> dict[str, Any]:
        voice = getattr(self.voice, "elevenlabs", None)
        take_audio = getattr(voice, "take_audio", None)
        if not callable(take_audio):
            return {"ok": True, "items": []}
        try:
            return {"ok": True, "items": take_audio()}
        except Exception:
            return {"ok": True, "items": []}

    def elevenlabs_status(self) -> dict[str, Any]:
        voice = getattr(self.voice, "elevenlabs", None)
        status = getattr(voice, "status", None)
        return status() if callable(status) else {"ok": True, "provider": "ElevenLabs", "configured": False}

    def configure_elevenlabs(self, api_key: str, voice_id: str = "", model_id: str = "") -> dict[str, Any]:
        voice = getattr(self.voice, "elevenlabs", None)
        configure = getattr(voice, "configure", None)
        if not callable(configure):
            raise RuntimeError("ElevenLabs voice engine is unavailable")
        result = configure(api_key, voice_id=voice_id or None, model_id=model_id or None)
        test = self.test_elevenlabs()
        result["tested"] = bool(test.get("ok"))
        result["message"] = "ElevenLabs voice connected and speech-tested" if result["tested"] else "ElevenLabs key saved; speech test failed"
        return result

    def test_elevenlabs(self) -> dict[str, Any]:
        voice = getattr(self.voice, "elevenlabs", None)
        test = getattr(voice, "test_speech", None)
        return test() if callable(test) else {"ok": False, "tested": False, "message": "ElevenLabs voice engine is unavailable"}

    def elevenlabs_voices(self) -> dict[str, Any]:
        voice = getattr(self.voice, "elevenlabs", None)
        client = getattr(voice, "client", None)
        list_voices = getattr(client, "list_voices", None)
        if not callable(list_voices):
            return {"ok": False, "voices": []}
        try:
            return {"ok": True, "voices": list_voices()}
        except Exception:
            return {"ok": False, "voices": []}

    def open_omniroute_dashboard(self) -> dict[str, Any]:
        import webbrowser
        webbrowser.open("http://127.0.0.1:20128")
        return {"ok": True}

    def _warm_omniroute(self) -> None:
        try:
            if self.omniroute.ensure_running(wait_seconds=30):
                LOGGER.info("embedded OmniRoute warm-up passed")
            else:
                LOGGER.warning("embedded OmniRoute warm-up did not complete before timeout")
        except Exception:
            LOGGER.exception("embedded OmniRoute warm-up failed; routing remains retryable")

    def open_omniroute_settings(self) -> dict[str, Any]:
        try:
            import webview
            with self._floating_lock:
                if self._omniroute_settings_window is not None:
                    try:
                        self._omniroute_settings_window.restore()
                        self._omniroute_settings_window.show()
                    except Exception:
                        pass
                    return {"ok": True}
                self._omniroute_settings_window = webview.create_window(
                    "Jarvis AI Providers",
                    html=OMNIROUTE_SETTINGS_HTML,
                    js_api=self._web_api,
                    width=560,
                    height=640,
                    resizable=True,
                    frameless=False,
                    easy_drag=True,
                    on_top=False,
                )
                try:
                    self._omniroute_settings_window.events.closed += self._on_omniroute_settings_closed
                except Exception:
                    LOGGER.debug("OmniRoute settings window does not expose a closed event")
            return {"ok": True}
        except Exception as exc:
            LOGGER.exception("OmniRoute settings window could not open")
            raise RuntimeError("AI provider settings could not be opened") from exc

    def _on_omniroute_settings_closed(self, *_args: Any, **_kwargs: Any) -> None:
        with self._floating_lock:
            self._omniroute_settings_window = None

    @staticmethod
    def _exit_for_update() -> None:
        logging.shutdown()
        os._exit(0)

    def start(self) -> None:
        if self.started:
            return
        self.visualizer.start()
        warm_setting = os.environ.get("JARVIS_OMNIROUTE_WARMUP", "").strip().lower()
        smoke = os.environ.get("JARVIS_SMOKE", "0").strip().lower() in {"1", "true", "yes", "on"}
        warm_enabled = bool(getattr(sys, "frozen", False)) and warm_setting not in {"0", "false", "no", "off"} and (
            warm_setting in {"1", "true", "yes", "on"} or not smoke
        )
        if warm_enabled:
            self._omniroute_warmup_thread = threading.Thread(target=self._warm_omniroute, name="jarvis-omniroute-warmup", daemon=True)
            self._omniroute_warmup_thread.start()
        try:
            self.voice.start()
        except Exception:
            LOGGER.exception("optional voice component could not start; continuing with Fullstack visualizer")
        try:
            self.hands.start()
        except Exception:
            LOGGER.exception("optional hand-control component could not start")
        try:
            self.updater.start()
        except Exception:
            LOGGER.exception("auto-update monitor could not start; current Jarvis remains running")
        self.started = True
        self.stopped = False

    def stop(self) -> None:
        if self.stopped:
            return
        self._shutting_down = True
        self.floating_hotkey.stop()
        with self._floating_lock:
            if self._omniroute_settings_window is not None:
                try:
                    self._omniroute_settings_window.destroy()
                except Exception:
                    LOGGER.exception("OmniRoute settings window failed to close cleanly")
                self._omniroute_settings_window = None
        with self._floating_lock:
            self._save_floating_position()
            if self._floating_window is not None:
                try:
                    self._floating_window.destroy()
                except Exception:
                    LOGGER.exception("floating command bar failed to close cleanly")
                self._floating_window = None
        self.updater.stop()
        if self._omniroute_warmup_thread is not None and self._omniroute_warmup_thread.is_alive() and threading.current_thread() is not self._omniroute_warmup_thread:
            self._omniroute_warmup_thread.join(timeout=2)
        self._omniroute_warmup_thread = None
        try:
            save = getattr(self._web_api, "neural_world_save", None)
            if callable(save):
                save()
        except Exception:
            LOGGER.exception("neural world persistence failed during shutdown")
        for component in (self.hands, self.voice, self.visualizer):
            try:
                component.stop()
            except Exception:
                LOGGER.exception("fullstack component failed during shutdown")
        try:
            restore = getattr(self._web_api, "spatial_unembed_all", None)
            if callable(restore):
                restore()
        except Exception:
            LOGGER.exception("failed to restore spatial application windows")
        self.controller.close()
        self.stopped = True
        self.started = False

    @staticmethod
    def _fullscreen_enabled() -> bool:
        return os.environ.get("JARVIS_FULLSCREEN", "0").strip().lower() in {"1", "true", "yes", "on"}

    def _load_floating_position(self) -> tuple[int | None, int | None]:
        try:
            payload = json.loads(FLOATING_POSITION_FILE.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return None, None
            x, y = payload.get("x"), payload.get("y")
            if type(x) is int and type(y) is int:
                return x, y
        except (OSError, ValueError, TypeError):
            pass
        return None, None

    def _save_floating_position(self) -> None:
        window = self._floating_window
        if window is None:
            return
        try:
            x, y = int(window.x), int(window.y)
            FLOATING_POSITION_FILE.parent.mkdir(parents=True, exist_ok=True)
            FLOATING_POSITION_FILE.write_text(json.dumps({"x": x, "y": y}), encoding="utf-8")
        except Exception:
            LOGGER.exception("could not persist floating command bar position")

    def _create_floating_window(self, webview: Any) -> Any:
        with self._floating_lock:
            if self._floating_window is not None:
                return self._floating_window
            x, y = self._load_floating_position()
            kwargs: dict[str, Any] = {
                "title": "Jarvis Floating Text Link",
                "html": FLOATING_TEXT_INPUT_HTML,
                "js_api": self.web_api,
                "width": 620,
                "height": 112,
                "resizable": True,
                "min_size": (460, 96),
                "hidden": True,
                "frameless": True,
                "easy_drag": True,
                "shadow": True,
                "on_top": True,
                "background_color": "#030806",
            }
            if x is not None and y is not None:
                kwargs["x"], kwargs["y"] = x, y
            self._floating_window = webview.create_window(**kwargs)
            events = getattr(self._floating_window, "events", None)
            if events is not None:
                events.moved += self._on_floating_moved
                events.closing += self._on_floating_closing
                events.loaded += self._on_floating_loaded
            else:
                LOGGER.debug("floating command bar mock window exposes no event container")
            LOGGER.info("floating command bar window object created; pid=%s hotkey=%s", os.getpid(), FLOATING_HOTKEY_LABEL)
            return self._floating_window

    def _on_floating_loaded(self, *_args: Any, **_kwargs: Any) -> None:
        LOGGER.info("floating command bar DOM loaded")
        if self._floating_visible and self._floating_window is not None:
            try:
                self._floating_window.evaluate_js("window.setTimeout(function(){var e=document.getElementById('input'); if(e)e.focus();},80);")
            except Exception:
                pass

    def _on_floating_moved(self, *_args: Any, **_kwargs: Any) -> None:
        self._save_floating_position()

    def _on_floating_closing(self, *_args: Any, **_kwargs: Any) -> bool | None:
        if self._shutting_down:
            return True
        self._floating_visible = False
        try:
            if self._floating_window is not None:
                self._save_floating_position()
                self._floating_window.hide()
            self._show_main_text_link()
        except Exception:
            LOGGER.exception("could not convert floating command bar close into a hide action")
        return False

    def _show_main_text_link(self) -> None:
        window = self._window
        if window is None:
            return
        try:
            window.evaluate_js("window.jarvisTextInput && window.jarvisTextInput.setVisible(true); window.jarvisNeuralCommandSurface && window.jarvisNeuralCommandSurface.setVisible(true); window.jarvisNeuralCommandSurface && window.jarvisNeuralCommandSurface.focus(); window.jarvisTextInput && window.jarvisTextInput.focus();")
        except Exception:
            LOGGER.exception("could not restore in-app Jarvis text link")

    def _hide_main_text_link(self) -> None:
        window = self._window
        if window is None:
            return
        try:
            window.evaluate_js("window.jarvisTextInput && window.jarvisTextInput.setVisible(false); window.jarvisNeuralCommandSurface && window.jarvisNeuralCommandSurface.setVisible(false);")
        except Exception:
            LOGGER.exception("could not hide in-app Jarvis text link")

    def _toggle_text_link_from_hotkey(self) -> None:
        self.toggle_text_link(None)

    def toggle_text_link(self, detached: bool | None = None) -> dict[str, Any]:
        with self._floating_lock:
            target = (not self._floating_visible) if detached is None else bool(detached)
            window = self._floating_window
            if window is None:
                import webview
                window = self._create_floating_window(webview)
            self._floating_visible = target
            if target:
                self._hide_main_text_link()
                try:
                    window.on_top = True
                except Exception:
                    pass
                window.show()
                try:
                    window.evaluate_js("window.setTimeout(function(){var e=document.getElementById('input'); if(e)e.focus();},80);")
                except Exception:
                    pass
                LOGGER.info("floating command bar shown")
            else:
                self._save_floating_position()
                window.hide()
                self._show_main_text_link()
                LOGGER.info("floating command bar hidden")
            return self.text_link_state()

    def text_link_state(self) -> dict[str, Any]:
        return {
            "ok": True,
            "floating": bool(self._floating_visible),
            "hotkey": FLOATING_HOTKEY_LABEL,
            "position_persisted": FLOATING_POSITION_FILE.exists(),
        }

    def _on_main_window_closing(self, *_args: Any, **_kwargs: Any) -> None:
        """Destroy the hidden floating bar when the main Jarvis window closes."""
        self._shutting_down = True
        self._floating_visible = False
        with self._floating_lock:
            self._save_floating_position()
            floating = self._floating_window
            self._floating_window = None
            if floating is not None:
                try:
                    floating.destroy()
                except Exception:
                    LOGGER.exception("floating command bar failed to close with the main Jarvis window")

    def _on_window_before_show(self, window: Any) -> None:
        try:
            native = getattr(window, "native", None)
            handle = int(native.Handle.ToInt64())
            setter = getattr(self._web_api, "spatial_set_host_handle", None)
            if callable(setter):
                setter(handle)
            LOGGER.info("native Jarvis host handle registered for spatial windows: %s", handle)
        except Exception:
            LOGGER.exception("could not register native Jarvis host handle for spatial windows")

    def _on_window_loaded(self, *_args: Any, **_kwargs: Any) -> None:
        window = self._window
        if window is None:
            return
        try:
            window.evaluate_js(TEXT_INPUT_SCRIPT)
            LOGGER.info("centered Jarvis text input overlay injected")
        except Exception:
            LOGGER.exception("centered Jarvis text input overlay failed to inject")

    @staticmethod
    def _native_window_kwargs(url: str, fullscreen: bool) -> dict[str, Any]:
        """Return the exact native pywebview window contract used by production."""
        return {
            "title": "Jarvis",
            "url": url,
            "width": 1200,
            "height": 800,
            "fullscreen": fullscreen,
            "resizable": True,
            "min_size": (800, 600),
        }

    def run_window(self) -> None:
        """Create the native visualizer window on the foreground thread."""
        headless_smoke = os.environ.get("JARVIS_UI_SMOKE", "0").strip().lower() in {"1", "true", "yes", "on"}
        try:
            import webview
        except ImportError as exc:
            raise RuntimeError("pywebview is required for the native Jarvis window") from exc

        gui = "edgechromium" if sys.platform == "win32" else None
        window_kwargs = self._native_window_kwargs(self.visualizer.url(), self._fullscreen_enabled())
        window_kwargs["js_api"] = self.web_api

        if headless_smoke:
            # GitHub-hosted Windows runners do not provide a trustworthy interactive
            # desktop/visible HWND. Still exercise the real frozen pywebview
            # construction path with the exact production kwargs, but do not start
            # its GUI event loop in the hosted runner session.
            if VoiceAdapter._truthy("JARVIS_SMOKE_WEBVIEW"):
                LOGGER.info("frozen pywebview import validation passed: %s", getattr(webview, "__version__", "unknown"))
            required = {"title", "url", "width", "height", "fullscreen", "resizable", "min_size", "js_api"}
            if set(window_kwargs) != required:
                raise RuntimeError(f"native Jarvis window contract mismatch: {sorted(window_kwargs)}")
            if window_kwargs["title"] != "Jarvis" or window_kwargs["width"] < 800 or window_kwargs["height"] < 600:
                raise RuntimeError("native Jarvis window contract has invalid title or size")

            LOGGER.info(
                "constructing frozen Jarvis native window object; gui=%s url=%s size=%sx%s",
                gui or "default",
                window_kwargs["url"],
                window_kwargs["width"],
                window_kwargs["height"],
            )
            self._window = webview.create_window(**window_kwargs)
            if self._window is None:
                raise RuntimeError("pywebview returned no Jarvis window object")
            if getattr(self._window, "title", "Jarvis") != "Jarvis":
                raise RuntimeError("pywebview returned a native Jarvis window with the wrong title")
            try:
                self._window.events.before_show += self._on_window_before_show
                self._window.events.loaded += self._on_window_loaded
                self._window.events.closing += self._on_main_window_closing
            except Exception:
                LOGGER.exception("could not attach Jarvis text input loaded callback")
            self._create_floating_window(webview)
            LOGGER.info(
                "headless frozen Jarvis native window object created; gui=%s url=%s size=%sx%s",
                gui or "default",
                window_kwargs["url"],
                window_kwargs["width"],
                window_kwargs["height"],
            )
            threading.Event().wait()
            return

        LOGGER.info(
            "creating native Jarvis window; gui=%s fullscreen=%s url=%s",
            gui or "default",
            self._fullscreen_enabled(),
            self.visualizer.url(),
        )
        self._window = webview.create_window(**window_kwargs)
        try:
            self._window.events.before_show += self._on_window_before_show
            self._window.events.loaded += self._on_window_loaded
            self._window.events.closing += self._on_main_window_closing
        except Exception:
            LOGGER.exception("could not attach Jarvis text input loaded callback")
        self._create_floating_window(webview)
        self.floating_hotkey.start()
        LOGGER.info("native Jarvis window object created; floating text link ready; hotkey=%s", FLOATING_HOTKEY_LABEL)
        if gui is None:
            webview.start(debug=False)
        else:
            webview.start(gui=gui, debug=False)
        LOGGER.info("native Jarvis GUI event loop exited")


def main() -> int:
    visualizer = VisualizerAdapter()
    host: FullstackJarvisHost | None = None
    try:
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
