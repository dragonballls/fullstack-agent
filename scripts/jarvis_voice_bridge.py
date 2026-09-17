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


DEFAULT_CONFIG: dict[str, Any] = {
    "name": "JARVIS",
    "ptt_key": "home",
    "mic_mode": "ptt",
    "voice": "bm_lewis",
    "stt_model": "small.en",
    "stt_device": "cpu",
    "stt_compute": "int8",
    "greeting": "Hello. I'm online and ready.",
    "greeting_open_mic": "",
}


def _log(message: str) -> None:
    try:
        log_dir = APP_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "voice-bridge.log").open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except OSError:
        pass


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
                    **DEFAULT_CONFIG,
                    "name": os.environ.get("JARVIS_NAME", DEFAULT_CONFIG["name"]),
                    "ptt_key": os.environ.get("JARVIS_PTT_KEY", DEFAULT_CONFIG["ptt_key"]),
                    "mic_mode": os.environ.get("JARVIS_MIC_MODE", DEFAULT_CONFIG["mic_mode"]),
                    "voice": os.environ.get("JARVIS_VOICE", DEFAULT_CONFIG["voice"]),
                    "stt_model": os.environ.get("JARVIS_STT_MODEL", DEFAULT_CONFIG["stt_model"]),
                    "stt_device": os.environ.get("JARVIS_STT_DEVICE", DEFAULT_CONFIG["stt_device"]),
                    "stt_compute": os.environ.get("JARVIS_STT_COMPUTE", DEFAULT_CONFIG["stt_compute"]),
                    "signals_dir": str(SIGNALS_DIR),
                    "thinking_sound": "",
                    "elevenlabs": {"enabled": False, "voice_id": ""},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    os.environ["BACKTALK_CONFIG"] = str(BACKTALK_CONFIG)
    return vendor


def _migrate_legacy_stt_default(config: dict[str, Any]) -> dict[str, Any]:
    """Move legacy auto/CPU-incompatible STT settings to stable CPU mode."""
    if os.environ.get("JARVIS_STT_DEVICE"):
        return config
    device = str(config.get("stt_device", "")).strip().lower()
    compute = str(config.get("stt_compute", "")).strip().lower()
    if device != "auto" and not (device == "cpu" and compute == "float16"):
        return config
    migrated = dict(config)
    migrated["stt_device"] = "cpu"
    migrated["stt_compute"] = "int8"
    try:
        BACKTALK_CONFIG.write_text(json.dumps(migrated, indent=2) + "\n", encoding="utf-8")
        _log(
            "migrated legacy STT settings to cpu/int8 for stable Windows voice startup "
            f"(was {device or 'unset'}/{compute or 'unset'})"
        )
    except OSError as exc:
        _log(f"could not persist STT migration: {type(exc).__name__}: {exc}")
    return migrated


class JarvisVoiceBridge:
    """Run Fullstack ears/mouth while every request goes to Jarvis."""

    def __init__(
        self,
        controller: Any,
        ears: Any | None = None,
        mouth: Any | None = None,
        ptt: Any | None = None,
        confirmation: Callable[[str], bool] | None = None,
        record_held: Callable[[Callable[[], bool]], str] | None = None,
    ) -> None:
        self.controller = controller
        self.ears = ears
        self.mouth = mouth
        self.ptt = ptt
        self.confirmation = confirmation or self._native_confirmation
        self.record_held = record_held
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.stopped = False
        self.config: dict[str, Any] = dict(DEFAULT_CONFIG)

    def _load_components(self) -> None:
        needs_vendor = self.ears is None or self.mouth is None or (
            os.environ.get("JARVIS_MIC_MODE", self.config.get("mic_mode", "ptt")) != "open"
            and self.ptt is None
        )
        if needs_vendor:
            vendor = _configure_vendor()
            try:
                from backtalk.config import CFG
                self.config = _migrate_legacy_stt_default(dict(CFG))
                CFG["stt_device"] = self.config["stt_device"]
                CFG["stt_compute"] = self.config.get("stt_compute", "int8")
                _log(
                    f"Backtalk voice components configured from {vendor}; "
                    f"stt_device={CFG['stt_device']} stt_compute={CFG['stt_compute']}"
                )
            except Exception as exc:
                self.config = dict(DEFAULT_CONFIG)
                _log(f"could not load Backtalk config: {type(exc).__name__}: {exc}")
        else:
            self.config = dict(DEFAULT_CONFIG)

        if self.ears is None:
            from backtalk.ears import Ears
            self.ears = Ears()
        if self.mouth is None:
            from backtalk.mouth import Mouth
            self.mouth = Mouth()

        mode = os.environ.get("JARVIS_MIC_MODE", str(self.config.get("mic_mode", "ptt"))).strip().lower()
        if mode != "open" and self.ptt is None:
            from backtalk.ptt import PTTListener
            self.ptt = PTTListener(os.environ.get("JARVIS_PTT_KEY", str(self.config.get("ptt_key", "home"))))

        if mode != "open" and self.record_held is None:
            from backtalk.ears import record_held
            self.record_held = record_held

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
        mode = os.environ.get("JARVIS_MIC_MODE", str(self.config.get("mic_mode", "ptt"))).strip().lower()
        greeting_key = "greeting_open_mic" if mode == "open" else "greeting"
        greeting = str(self.config.get(greeting_key) or self.config.get("greeting") or "")
        greeting = greeting.replace("{ptt_key}", str(self.config.get("ptt_key", "home")))
        if greeting:
            self._speak(greeting)
        self.thread = threading.Thread(target=self._run, name="jarvis-voice", daemon=True)
        self.thread.start()

    def _speak(self, text: str) -> None:
        if self.mouth is None or not text:
            return
        try:
            self.mouth.say(text)
        except Exception as exc:
            _log(f"speech output error: {type(exc).__name__}: {exc}")

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
        mode = os.environ.get("JARVIS_MIC_MODE", str(self.config.get("mic_mode", "ptt"))).strip().lower()
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
                recorder = self.record_held
                if recorder is None:
                    raise RuntimeError("Fullstack push-to-talk recorder is unavailable")
                text = recorder(self.ptt.is_held)
                if text:
                    self.handle_transcript(text)
            except Exception as exc:
                self._log(f"ptt error: {type(exc).__name__}: {exc}")
                self.stop_event.wait(1.0)

    @staticmethod
    def _log(message: str) -> None:
        _log(message)

    def stop(self) -> None:
        if self.stopped:
            return
        self.stop_event.set()
        try:
            if self.ptt is not None:
                listener = getattr(self.ptt, "_listener", None)
                stop_listener = getattr(listener, "stop", None)
                if callable(stop_listener):
                    stop_listener()
        except Exception as exc:
            self._log(f"PTT listener shutdown failed: {type(exc).__name__}: {exc}")
        try:
            if self.mouth is not None:
                self.mouth.shut_up()
                shutdown = getattr(self.mouth, "shutdown", None)
                if callable(shutdown):
                    shutdown()
                drop_out = getattr(self.mouth, "_drop_out", None)
                if callable(drop_out):
                    drop_out()
        except Exception as exc:
            self._log(f"mouth shutdown failed: {type(exc).__name__}: {exc}")
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=3)
        self.stopped = True
