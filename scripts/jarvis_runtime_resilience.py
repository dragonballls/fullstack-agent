from __future__ import annotations

import importlib
import os
import threading
from typing import Any

from scripts.jarvis_voice_bridge import JarvisVoiceBridge as _JarvisVoiceBridge


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
                result = self.host.controller.execute_request(normalized, confirmed=bool(confirmed))
                return self._payload(result)
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}".replace("OPENAI_API_KEY", "[secret]")
                return {"ok": False, "error": message[:500], "needs_confirmation": False}


class JarvisResilientVoiceBridge(_JarvisVoiceBridge):
    """Preflight speech recognition before listening so STT failures degrade voice only."""

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
            self.stop_event.set()
            self._log(
                "voice STT preflight failed; voice input disabled while Jarvis stays running: "
                f"{type(exc).__name__}: {str(exc)[:400]}"
            )
            return False

    def _run(self) -> None:
        if not self._prepare_stt():
            return
        super()._run()


# Runs after the original Fullstack text-link script so its existing
# submission/confirmation behavior is preserved and only the interaction
# contract is changed.
TEXT_INPUT_RESILIENCE_SCRIPT = r'''
(function () {
  "use strict";
  if (window.__jarvisTextResilienceInstalled) return;
  window.__jarvisTextResilienceInstalled = true;

  const shell = document.getElementById("jarvis-text-shell");
  if (!shell) return;
  const input = document.getElementById("jarvis-text-input");
  if (!input) return;

  const style = document.createElement("style");
  style.id = "jarvis-text-resilience-style";
  style.textContent = `
    #jarvis-hover-zone {
      position: fixed;
      z-index: 2147483646;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      width: min(36vw, 560px);
      height: min(22vh, 210px);
      min-width: 280px;
      min-height: 120px;
      border-radius: 24px;
      background: transparent;
      pointer-events: auto;
    }
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
  `;
  document.head.appendChild(style);

  const zone = document.createElement("div");
  zone.id = "jarvis-hover-zone";
  zone.setAttribute("aria-hidden", "true");
  document.body.appendChild(zone);

  let insideZone = false;
  let insideShell = false;
  let timer = null;

  function active() {
    clearTimeout(timer);
    shell.classList.add("jarvis-active");
  }

  function maybeHide() {
    clearTimeout(timer);
    timer = setTimeout(function () {
      if (!insideZone && !insideShell && document.activeElement !== input) {
        shell.classList.remove("jarvis-active");
      }
    }, 120);
  }

  zone.addEventListener("mouseenter", function () {
    insideZone = true;
    active();
  });
  zone.addEventListener("mouseleave", function () {
    insideZone = false;
    maybeHide();
  });
  shell.addEventListener("mouseenter", function () {
    insideShell = true;
    active();
  });
  shell.addEventListener("mouseleave", function () {
    insideShell = false;
    maybeHide();
  });
  input.addEventListener("focus", function () {
    active();
  });
  input.addEventListener("blur", maybeHide);

  function blockCinematicSpace(event) {
    if (event.key === " " || event.code === "Space") {
      event.stopImmediatePropagation();
    }
  }

  input.addEventListener("keydown", blockCinematicSpace);
  input.addEventListener("keyup", blockCinematicSpace);
  input.addEventListener("keypress", blockCinematicSpace);
  document.addEventListener("keydown", function (event) {
    if (document.activeElement === input && (event.key === " " || event.code === "Space")) {
      event.stopImmediatePropagation();
    }
  }, true);
  document.addEventListener("keyup", function (event) {
    if (document.activeElement === input && (event.key === " " || event.code === "Space")) {
      event.stopImmediatePropagation();
    }
  }, true);

  // The visualizer draws the JARVIS chip into the center canvas, so the
  // transparent hit zone deliberately tracks that center instead of a HUD
  // element that sits elsewhere on the screen.
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
