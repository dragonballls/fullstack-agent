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
    """Lazy bridge to the embedded upstream backtalk ears/mouth."""

    def __init__(self, controller: JarvisDesktopController) -> None:
        self.controller = controller
        self.bridge: Any | None = None

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
        LOGGER.info("embedded Backtalk smoke validation passed: %s", vendor)

    def start(self) -> None:
        if self._truthy("JARVIS_SMOKE") and self._truthy("JARVIS_SMOKE_VOICE"):
            self._smoke_validate_embedded_backtalk()
            return
        if self._truthy("JARVIS_DISABLE_VOICE"):
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
    #jarvis-text-shell {
      position: fixed;
      z-index: 2147483647;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      width: min(320px, calc(100vw - 36px));
      padding: 10px;
      border: 1px solid rgba(61,220,132,.20);
      border-radius: 14px;
      background: rgba(2,7,5,.46);
      box-shadow: 0 0 24px rgba(61,220,132,.08), inset 0 0 18px rgba(61,220,132,.03);
      backdrop-filter: blur(8px);
      opacity: .42;
      transition: width .22s ease, opacity .22s ease, border-color .22s ease, box-shadow .22s ease;
      pointer-events: auto;
      font-family: var(--mono, Consolas, monospace);
      color: #e8f0f2;
    }
    #jarvis-text-shell:hover,
    #jarvis-text-shell.jarvis-active {
      width: min(640px, calc(100vw - 36px));
      opacity: 1;
      border-color: rgba(61,220,132,.56);
      box-shadow: 0 0 34px rgba(61,220,132,.18), inset 0 0 22px rgba(61,220,132,.05);
    }
    #jarvis-text-label {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 3px 7px;
      font-size: 9px;
      letter-spacing: .28em;
      color: #8fc4a8;
      user-select: none;
    }
    #jarvis-text-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #3ddc84;
      box-shadow: 0 0 10px rgba(61,220,132,.55);
      flex: 0 0 auto;
    }
    #jarvis-text-row {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    #jarvis-text-input {
      min-width: 0;
      flex: 1;
      border: 1px solid rgba(143,232,184,.22);
      outline: none;
      border-radius: 9px;
      padding: 12px 13px;
      color: #e8f0f2;
      background: rgba(0,0,0,.28);
      font: inherit;
      font-size: 13px;
      letter-spacing: .04em;
      cursor: text;
      caret-color: #8fe8b8;
    }
    #jarvis-text-input::placeholder { color: #6d8580; }
    #jarvis-text-input:focus { border-color: rgba(143,232,184,.58); box-shadow: 0 0 18px rgba(61,220,132,.10); }
    #jarvis-text-send {
      flex: 0 0 auto;
      width: 42px;
      height: 42px;
      border: 1px solid rgba(143,232,184,.28);
      border-radius: 9px;
      color: #a6ffd0;
      background: rgba(61,220,132,.06);
      cursor: pointer;
      font: inherit;
      font-size: 16px;
    }
    #jarvis-text-send:hover { border-color: rgba(143,232,184,.68); background: rgba(61,220,132,.13); }
    #jarvis-text-status {
      margin: 7px 3px 0;
      min-height: 14px;
      max-height: 44px;
      overflow: hidden;
      font-size: 9px;
      line-height: 1.45;
      letter-spacing: .10em;
      color: #839b94;
      white-space: pre-wrap;
    }
    #jarvis-text-status.jarvis-error { color: #ff8c98; }
    #jarvis-text-hint {
      margin: 7px 3px 0;
      font-size: 8px;
      letter-spacing: .17em;
      color: #566a64;
      user-select: none;
    }
  `;
  document.head.appendChild(style);

  const shell = document.createElement("div");
  shell.id = "jarvis-text-shell";
  shell.innerHTML = `
    <div id="jarvis-text-label"><span id="jarvis-text-dot"></span>JARVIS TEXT LINK</div>
    <div id="jarvis-text-row">
      <input id="jarvis-text-input" type="text" autocomplete="off" spellcheck="false" placeholder="Hover here and type to talk to Jarvis..." aria-label="Talk to Jarvis by text" disabled />
      <button id="jarvis-text-send" type="button" aria-label="Send text to Jarvis" disabled>↵</button>
    </div>
    <div id="jarvis-text-status"></div>
    <div id="jarvis-text-hint">ENTER — SEND &nbsp;&nbsp; ESC — CLEAR</div>
  `;
  document.body.appendChild(shell);

  const input = shell.querySelector("#jarvis-text-input");
  const send = shell.querySelector("#jarvis-text-send");
  const status = shell.querySelector("#jarvis-text-status");
  let apiReady = false;

  function setActive(active) {
    if (active) shell.classList.add("jarvis-active");
    else if (document.activeElement !== input) shell.classList.remove("jarvis-active");
  }

  async function submit(confirmed) {
    const text = input.value.trim();
    if (!text || !apiReady) return;
    setActive(true);
    input.disabled = true;
    send.disabled = true;
    status.classList.remove("jarvis-error");
    status.textContent = "PROCESSING...";
    try {
      let result = await window.pywebview.api.submit_text(text, !!confirmed);
      if (result && result.needs_confirmation && !confirmed) {
        status.textContent = result.text || "Confirmation required.";
        const accepted = window.confirm(result.text || "Jarvis requires confirmation for this action.");
        if (accepted) {
          result = await window.pywebview.api.submit_text(text, true);
        } else {
          status.textContent = "CANCELLED";
          result = null;
        }
      }
      if (result) {
        if (result.ok) {
          status.textContent = result.text || "DONE";
          input.value = "";
        } else {
          status.classList.add("jarvis-error");
          status.textContent = result.error || "Jarvis request failed.";
        }
      }
    } catch (error) {
      status.classList.add("jarvis-error");
      status.textContent = "TEXT LINK ERROR: " + String(error);
    } finally {
      input.disabled = false;
      send.disabled = false;
      input.focus();
    }
  }

  shell.addEventListener("mouseenter", function () { setActive(true); });
  shell.addEventListener("mouseleave", function () { setActive(false); });
  shell.addEventListener("focusin", function () { setActive(true); });
  shell.addEventListener("focusout", function () { setTimeout(function () { setActive(false); }, 0); });
  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      submit(false);
    } else if (event.key === "Escape") {
      event.preventDefault();
      input.value = "";
      status.textContent = "";
      input.blur();
    }
  });
  send.addEventListener("click", function () { submit(false); });

  function markReady() {
    apiReady = !!(window.pywebview && window.pywebview.api);
    input.disabled = !apiReady;
    send.disabled = !apiReady;
    if (apiReady) {
      status.textContent = "READY — TEXT LINK ONLINE";
    }
  }

  window.addEventListener("pywebviewready", markReady, { once: true });
  if (window.pywebview && window.pywebview.api) markReady();
})();
'''


\nFLOATING_TEXT_INPUT_HTML = r'''<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n<title>Jarvis Floating Text Link</title>\n<style>\n*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#030806;color:#e8f0f2;font-family:Consolas,"SFMono-Regular",monospace}#frame{width:100%;height:100%;padding:10px;border:1px solid rgba(61,220,132,.28);border-radius:16px;background:linear-gradient(145deg,rgba(5,17,12,.98),rgba(2,7,5,.96));box-shadow:0 12px 36px rgba(0,0,0,.5),inset 0 0 24px rgba(61,220,132,.05)}#bar{display:flex;align-items:center;gap:9px;margin-bottom:8px;cursor:move;user-select:none}.pywebview-drag-region{cursor:move}.dot{width:7px;height:7px;border-radius:50%;background:#3ddc84;box-shadow:0 0 11px rgba(61,220,132,.7)}#title{flex:1;font-size:9px;letter-spacing:.22em;color:#8fc4a8}#hotkey{font-size:7px;letter-spacing:.09em;color:#5d756b}#close{width:24px;height:22px;border:1px solid rgba(255,255,255,.08);border-radius:6px;background:transparent;color:#789087;cursor:pointer;font:inherit}#close:hover{border-color:rgba(255,140,152,.38);color:#ff9aa5}#row{display:flex;gap:8px;align-items:center}#input{min-width:0;flex:1;height:42px;border:1px solid rgba(143,232,184,.28);border-radius:9px;outline:none;padding:0 13px;background:rgba(0,0,0,.28);color:#e8f0f2;font:inherit;font-size:13px;letter-spacing:.03em;caret-color:#8fe8b8}#input:focus{border-color:rgba(143,232,184,.72);box-shadow:0 0 18px rgba(61,220,132,.13)}#input::placeholder{color:#637a71}#send{width:44px;height:42px;border:1px solid rgba(143,232,184,.30);border-radius:9px;background:rgba(61,220,132,.07);color:#a6ffd0;cursor:pointer;font:inherit;font-size:17px}#send:hover{background:rgba(61,220,132,.15);border-color:rgba(143,232,184,.7)}#status{margin-top:7px;min-height:12px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;color:#78958a;font-size:8px;letter-spacing:.09em}#status.error{color:#ff8c98}</style>\n</head>\n<body><div id="frame"><div id="bar" class="pywebview-drag-region"><span class="dot"></span><span id="title">JARVIS FLOATING TEXT LINK</span><span id="hotkey">CTRL+ALT+SHIFT+F12</span><button id="close" type="button" aria-label="Return Jarvis text link to the main app">×</button></div><div id="row"><input id="input" type="text" autocomplete="off" spellcheck="false" placeholder="Talk to Jarvis from anywhere on your desktop…" disabled><button id="send" type="button" aria-label="Send text to Jarvis" disabled>↵</button></div><div id="status">CONNECTING…</div></div>\n<script>(function(){const input=document.getElementById("input"),send=document.getElementById("send"),close=document.getElementById("close"),status=document.getElementById("status");let ready=false;async function submit(confirmed){const text=input.value.trim();if(!text||!ready)return;input.disabled=true;send.disabled=true;status.classList.remove("error");status.textContent="PROCESSING…";try{let r=await window.pywebview.api.submit_text(text,!!confirmed);if(r&&r.needs_confirmation&&!confirmed){const ok=window.confirm(r.text||"Jarvis requires confirmation for this action.");if(ok)r=await window.pywebview.api.submit_text(text,true);else{status.textContent="CANCELLED";r=null}}if(r){if(r.ok){status.textContent=r.text||"DONE";input.value=""}else{status.classList.add("error");status.textContent=r.error||"Jarvis request failed."}}}catch(e){status.classList.add("error");status.textContent="TEXT LINK ERROR: "+String(e)}finally{input.disabled=false;send.disabled=false;input.focus()}}input.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();submit(false)}else if(e.key==="Escape"){e.preventDefault();input.value="";status.textContent="";input.blur()}});send.addEventListener("click",()=>submit(false));close.addEventListener("click",()=>{if(window.pywebview&&window.pywebview.api)window.pywebview.api.toggle_text_link(false)});function readyFn(){ready=!!(window.pywebview&&window.pywebview.api);input.disabled=!ready;send.disabled=!ready;if(ready){status.textContent="FLOATING TEXT LINK ONLINE";setTimeout(()=>input.focus(),80)}}window.addEventListener("pywebviewready",readyFn,{once:true});if(window.pywebview&&window.pywebview.api)readyFn()})();</script>\n</body></html>'''\n\nclass FullstackJarvisHost:
    """Lifecycle supervisor for the complete Jarvis Fullstack presentation."""

    def __init__(self, controller: JarvisDesktopController, *, visualizer: Any | None = None, voice: Any | None = None, hands: Any | None = None) -> None:
        self.controller = controller
        self.visualizer = visualizer or VisualizerAdapter()
        self.voice = voice or VoiceAdapter(controller)
        self.hands = hands or HandsAdapter(controller.runtime)
        self.started = False
        self.stopped = False
        self._window: Any | None = None
        self._web_api = JarvisWebApi(self)
        self._update_stop = threading.Event()
        self.updater = AutoUpdateController(self._update_stop, self._exit_for_update)

    @property
    def web_api(self) -> JarvisWebApi:
        return self._web_api

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
        self.updater.stop()
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
            except Exception:
                LOGGER.exception("could not attach Jarvis text input loaded callback")
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
        except Exception:
            LOGGER.exception("could not attach Jarvis text input loaded callback")
        LOGGER.info("native Jarvis window object created; entering GUI event loop")
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
