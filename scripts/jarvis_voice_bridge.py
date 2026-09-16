"""Bridge the upstream Fullstack voice I/O to the guarded Jarvis brain."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import threading
from typing import Any, Callable


APP_DIR = Path.home() / "AppData" / "Local" / "Jarvis"
SIGNALS_DIR = APP_DIR / "signals"
BACKTALK_CONFIG = APP_DIR / "backtalk.json"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _configure_vendor() -> Path:
    from scripts.fullstack_assets import embedded_path

    vendor = embedded_path("backtalk/source")
    if str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
    APP_DIR.mkdir(parents=True, exist_ok=True)
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    if not BACKTALK_CONFIG.exists():
        BACKTALK_CONFIG.write_text(
            json.dumps(
                {
                    "agent_dir": str(APP_DIR),
                    "name": os.environ.get("JARVIS_NAME", "JARVIS"),
                    "permission_mode": "ask",
                    "ptt_key": os.environ.get("JARVIS_PTT_KEY", "home"),
                    "mic_mode": os.environ.get("JARVIS_MIC_MODE", "ptt"),
                    "voice": os.environ.get("JARVIS_VOICE", "bm_lewis"),
                    "stt_model": os.environ.get("JARVIS_STT_MODEL", "small.en"),
                    "stt_device": os.environ.get("JARVIS_STT_DEVICE", "auto"),
                    "stt_compute": os.environ.get("JARVIS_STT_COMPUTE", "int8"),
                    "signals_dir": str(SIGNALS_DIR),
                    "thinking_sound": "",
                    "greeting": "Hello. I'm online and ready.",
                    "elevenlabs": {"enabled": False, "voice_id": ""},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    os.environ["BACKTALK_CONFIG"] = str(BACKTALK_CONFIG)
    return vendor


class JarvisVoiceBridge:
    """Run Fullstack ears/mouth while every request goes to Jarvis."""

    def __init__(
        self,
        controller: Any,
        ears: Any | None = None,
        mouth: Any | None = None,
        ptt: Any | None = None,
        confirmation: Callable[[str], bool] | None = None,
    ) -> None:
        self.controller = controller
        self.ears = ears
        self.mouth = mouth
        self.ptt = ptt
        self.confirmation = confirmation or self._native_confirmation
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.stopped = False

    def _load_components(self) -> None:
        if self.ears is not None and self.mouth is not None:
            return
        _configure_vendor()
        from backtalk.ears import Ears
        from backtalk.mouth import Mouth

        self.ears = Ears()
        self.mouth = Mouth()
        mode = os.environ.get("JARVIS_MIC_MODE", "ptt").strip().lower()
        if mode != "open" and self.ptt is None:
            from backtalk.ptt import PTTListener
            self.ptt = PTTListener(os.environ.get("JARVIS_PTT_KEY", "home"))

    @staticmethod
    def _native_confirmation(text: str) -> bool:
        try:
            import tkinter.messagebox as messagebox
            return bool(messagebox.askyesno("Confirm Jarvis action", text))
        except Exception:
            return False

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self._load_components()
        self.stop_event.clear()
        self.stopped = False
        self.thread = threading.Thread(target=self._run, name="jarvis-voice", daemon=True)
        self.thread.start()

    def _speak(self, text: str) -> None:
        if self.mouth is None or not text:
            return
        self.mouth.say(text)

    def handle_transcript(self, text: str) -> Any:
        text = text.strip()
        if not text:
            return None
        result = self.controller.execute_request(text, confirmed=False)
        if bool(getattr(result, "needs_confirmation", False)):
            question = str(getattr(result, "text", "This action requires confirmation."))
            self._speak(question)
            if not self.confirmation(text):
                self._speak("Cancelled.")
                return result
            result = self.controller.execute_request(text, confirmed=True)
        spoken = str(getattr(result, "text", result))
        self._speak(spoken)
        return result

    def _run(self) -> None:
        mode = os.environ.get("JARVIS_MIC_MODE", "ptt").strip().lower()
        if mode == "open":
            self._run_open_mic()
        else:
            self._run_ptt()

    def _run_open_mic(self) -> None:
        while not self.stop_event.is_set():
            try:
                text = self.ears.listen_once(timeout_s=2.0)
                if text:
                    self.handle_transcript(text)
            except Exception as exc:
                self._log(f"open-mic error: {type(exc).__name__}: {exc}")
                self.stop_event.wait(1.0)

    def _run_ptt(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.ptt.wait_press()
                if self.stop_event.is_set():
                    break
                if getattr(self.mouth, "speaking", False):
                    self.mouth.shut_up()
                text = self.ears.listen_once(timeout_s=30.0)
                if text:
                    self.handle_transcript(text)
            except Exception as exc:
                self._log(f"ptt error: {type(exc).__name__}: {exc}")
                self.stop_event.wait(1.0)

    @staticmethod
    def _log(message: str) -> None:
        try:
            log_dir = APP_DIR / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / "voice-bridge.log").open("a", encoding="utf-8") as handle:
                handle.write(message + "\n")
        except OSError:
            pass

    def stop(self) -> None:
        if self.stopped:
            return
        self.stop_event.set()
        try:
            if self.mouth is not None:
                self.mouth.shut_up()
                shutdown = getattr(self.mouth, "shutdown", None)
                if callable(shutdown):
                    shutdown()
        except Exception:
            self._log("mouth shutdown failed")
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=3)
        self.stopped = True
