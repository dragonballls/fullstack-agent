from __future__ import annotations

import importlib
import os
import threading
from types import MethodType
from typing import Any

from scripts.jarvis_voice_bridge import JarvisVoiceBridge as _JarvisVoiceBridge


_MOUTH_SENTINEL = object()
_OMNIROUTE_READY = threading.Event()


class JarvisResilientWebApi:
    """Text bridge that never routes through the microphone/audio stack."""

    def __init__(self, host: Any) -> None:
        self.host = host
        self._lock = threading.Lock()

    @staticmethod
    def _payload(result: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "text": str(getattr(result, "text", result)),
            "needs_confirmation": bool(getattr(result, "needs_confirmation", False)),
        }

    def submit_text(self, text: str, confirmed: bool = False) -> dict[str, Any]:
        normalized = str(text or "").strip()
        if not normalized:
            return {"ok": False, "error": "Enter a request first.", "needs_confirmation": False}
        with self._lock:
            try:
                _ensure_omniroute_once()
                result = self.host.controller.execute_request(normalized, confirmed=bool(confirmed))
                return self._payload(result)
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}".replace("OPENAI_API_KEY", "[secret]")
                return {"ok": False, "error": message[:500], "needs_confirmation": False}


def _patch_mouth_instance(mouth: Any) -> None:
    """Make the pinned Backtalk worker terminate synchronously during app exit."""
    if getattr(mouth, "_jarvis_lifecycle_patched", False):
        return

    q = getattr(mouth, "_q", None)
    worker = getattr(mouth, "_worker", None)
    original_get = getattr(q, "get", None)
    original_shutdown = getattr(mouth, "shutdown", None)
    if q is None or worker is None or not callable(original_get) or not callable(original_shutdown):
        return

    def get_with_shutdown(*args: Any, **kwargs: Any) -> Any:
        item = original_get(*args, **kwargs)
        if item is _MOUTH_SENTINEL:
            # SystemExit is deliberately used rather than a custom exception:
            # threading suppresses an expected SystemExit from its worker
            # exception hook, keeping shutdown clean in packaged builds.
            raise SystemExit()
        return item

    q.get = get_with_shutdown

    def shutdown(self: Any) -> None:
        if getattr(self, "_jarvis_shutdown_complete", False):
            return
        try:
            original_shutdown()
        finally:
            # The thread can already be blocked inside the Queue.get method that
            # existed before this lifecycle wrapper was installed. One sentinel
            # wakes that in-flight call; the second is consumed by the wrapper
            # on the worker's next loop iteration and terminates it cleanly.
            q.put(_MOUTH_SENTINEL)
            q.put(_MOUTH_SENTINEL)
            worker_thread = getattr(self, "_worker", None)
            if worker_thread is not None and worker_thread.is_alive() and threading.current_thread() is not worker_thread:
                worker_thread.join(timeout=5)
            drop_out = getattr(self, "_drop_out", None)
            if callable(drop_out):
                try:
                    drop_out()
                except Exception:
                    pass
            self._jarvis_shutdown_complete = True

    mouth.shutdown = MethodType(shutdown, mouth)
    mouth._jarvis_lifecycle_patched = True


class JarvisResilientVoiceBridge(_JarvisVoiceBridge):
    """Preflight speech recognition and cleanly stop embedded audio workers."""

    def _load_components(self) -> None:
        super()._load_components()
        if self.mouth is not None:
            _patch_mouth_instance(self.mouth)

    def _prepare_stt(self) -> bool:
        if os.environ.get("JARVIS_VOICE_PREFLIGHT", "1").strip().lower() in {"0", "false", "no", "off"}:
            return True
        try:
            ears_module = importlib.import_module("backtalk.ears")
            warm = getattr(ears_module, "warm", None)
            if callable(warm):
                warm()
            self._log("voice STT preflight passed before live listening")
            return True
        except Exception as exc:
            self._log(
                "voice STT preflight failed; voice input disabled while Jarvis stays running: "
                f"{type(exc).__name__}: {str(exc)[:400]}"
            )
            self.stop_event.set()
            return False

    def _run(self) -> None:
        while not self.stop_event.is_set():
            if self._prepare_stt():
                super()._run()
                return
            self.stop_event.wait(15.0)


def _ensure_omniroute_once() -> None:
    """Start an installed local OmniRoute gateway without opening a visible console."""
    if _OMNIROUTE_READY.is_set():
        return
    if os.environ.get("JARVIS_OMNIROUTE_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        return
    try:
        from quality_of_life.omniroute_lifecycle import OmniRouteLifecycle
        from quality_of_life.router import CloudModelRouter

        lifecycle = OmniRouteLifecycle(CloudModelRouter.omniroute_base_url())
        lifecycle.ensure_available()
        _OMNIROUTE_READY.set()
    except Exception as exc:
        try:
            from scripts.jarvis_voice_bridge import _log
            _log(f"OmniRoute startup check failed safely: {type(exc).__name__}: {str(exc)[:400]}")
        except Exception:
            pass


TEXT_INPUT_RESILIENCE_SCRIPT = r'''
(function () {
  "use strict";
  if (window.__jarvisTextResilienceInstalled) return;
  window.__jarvisTextResilienceInstalled = true;

  const shell = document.getElementById("jarvis-text-shell");
  if (!shell) return;
  const input = document.getElementById("jarvis-text-input");
  if (!input) return;

  const zone = document.createElement("div");
  zone.id = "jarvis-hover-zone";
  zone.setAttribute("aria-hidden", "true");

  const style = document.createElement("style");
  style.id = "jarvis-text-resilience-style";
  style.textContent = `
    #jarvis-text-shell {
      width: 0 !important;
      min-width: 0 !important;
      padding: 0 !important;
      opacity: 0 !important;
      border-color: transparent !important;
      box-shadow: none !important;
      pointer-events: none !important;
    }
    #jarvis-text-shell.jarvis-active {
      width: min(640px, calc(100vw - 36px)) !important;
      min-width: min(320px, calc(100vw - 36px)) !important;
      padding: 10px !important;
      opacity: 1 !important;
      border-color: rgba(61,220,132,.56) !important;
      box-shadow: 0 0 34px rgba(61,220,132,.18), inset 0 0 22px rgba(61,220,132,.05) !important;
      pointer-events: auto !important;
    }
    #jarvis-hover-zone {
      position: fixed !important;
      left: 50% !important;
      top: 50% !important;
      width: min(420px, 36vw) !important;
      height: min(190px, 28vh) !important;
      transform: translate(-50%, -50%) !important;
      pointer-events: none !important;
      z-index: 2147483646 !important;
    }
  `;
  document.head.appendChild(style);
  document.body.appendChild(zone);

  let centerHovered = false;
  let shellHovered = false;
  let timer = null;

  function active() {
    clearTimeout(timer);
    shell.classList.add("jarvis-active");
  }

  function maybeHide() {
    clearTimeout(timer);
    timer = setTimeout(function () {
      const inputFocused = document.activeElement === input;
      if (!centerHovered && !shellHovered && !inputFocused) {
        shell.classList.remove("jarvis-active");
      }
    }, 140);
  }

  document.addEventListener("mousemove", function (event) {
    const rect = zone.getBoundingClientRect();
    const next = event.clientX >= rect.left && event.clientX <= rect.right
      && event.clientY >= rect.top && event.clientY <= rect.bottom;
    if (next !== centerHovered) {
      centerHovered = next;
      if (centerHovered) active(); else maybeHide();
    }
  }, { passive: true });

  shell.addEventListener("mouseenter", function () {
    shellHovered = true;
    active();
  });
  shell.addEventListener("mouseleave", function () {
    shellHovered = false;
    maybeHide();
  });
  input.addEventListener("focus", active);
  input.addEventListener("blur", maybeHide);

  // The visualizer's cinematic shortcut is a bubbling keydown listener.
  // Stop propagation only from the focused text input. Do not preventDefault.
  // Ordinary spaces must remain browser-default text input behavior.
  input.addEventListener("keydown", function (event) {
    if (event.key === " " || event.code === "Space") {
      event.stopImmediatePropagation();
    }
  });
  input.addEventListener("keyup", function (event) {
    if (event.key === " " || event.code === "Space") {
      event.stopImmediatePropagation();
    }
  });
  input.addEventListener("keypress", function (event) {
    if (event.key === " " || event.code === "Space") {
      event.stopImmediatePropagation();
    }
  });
})();
'''


def install_desktop_resilience() -> None:
    from scripts import jarvis_desktop
    import scripts.jarvis_voice_bridge as voice_module

    jarvis_desktop.JarvisWebApi = JarvisResilientWebApi
    jarvis_desktop.TEXT_INPUT_SCRIPT = (
        jarvis_desktop.TEXT_INPUT_SCRIPT + "\n" + TEXT_INPUT_RESILIENCE_SCRIPT
    )
    voice_module.JarvisVoiceBridge = JarvisResilientVoiceBridge
    threading.Thread(target=_ensure_omniroute_once, name="jarvis-omniroute-start", daemon=True).start()
