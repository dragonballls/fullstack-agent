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

LIVE_MIC_MODES = {"live", "open", "handsfree", "hands-free"}


DEFAULT_CONFIG: dict[str, Any] = {
    "name": "JARVIS",
    "ptt_key": "home",
    "mic_mode": "open",
    "voice": "bm_lewis",
    "stt_model": "small.en",
    "stt_device": "cpu",
    "stt_compute": "int8",
    "greeting": "Hello. I'm online and listening.",
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
                    "mic_mode": "open" if os.environ.get("JARVIS_MIC_MODE", DEFAULT_CONFIG["mic_mode"]).strip().lower() in LIVE_MIC_MODES else "ptt",
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
        on_output: Callable[[str], None] | None = None,
    ) -> None:
        self.controller = controller
        self.ears = ears
        self.mouth = mouth
        self.ptt = ptt
        self.confirmation = confirmation or self._native_confirmation
        self.record_held = record_held
        self.on_output = on_output
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.stopped = False
        self._speak_lock = threading.RLock()
        self._last_spoken_text = ""
        self._last_spoken_at = 0.0
        self.config: dict[str, Any] = dict(DEFAULT_CONFIG)
        self._barge_event = threading.Event()
        self._ptt_thread: threading.Thread | None = None
        self._browser_audio_active = False

    def _mode(self) -> str:
        """Normalize Jarvis voice modes without leaking an upstream-only value."""
        raw = os.environ.get("JARVIS_MIC_MODE", str(self.config.get("mic_mode", "open"))).strip().lower()
        return "live" if raw in LIVE_MIC_MODES else "ptt"

    def _load_components(self) -> None:
        mode = self._mode()
        needs_vendor = self.ears is None or self.mouth is None or (
            mode == "ptt" and (self.ptt is None or self.record_held is None)
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

        mode = self._mode()
        if self.ptt is None:
            try:
                from backtalk.ptt import PTTListener
                self.ptt = PTTListener(
                    os.environ.get("JARVIS_PTT_KEY", str(self.config.get("ptt_key", "home")))
                )
            except Exception as exc:
                if mode == "ptt":
                    raise
                self._log(f"optional live barge-in key unavailable: {type(exc).__name__}: {exc}")
                self.ptt = None

        if self.record_held is None and self.ptt is not None:
            try:
                from backtalk.ears import record_held
                self.record_held = record_held
            except Exception as exc:
                if mode == "ptt":
                    raise
                self._log(f"optional live barge-in recorder unavailable: {type(exc).__name__}: {exc}")
                self.record_held = None

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
        self._barge_event.clear()
        self.stopped = False
        mode = self._mode()
        greeting_key = "greeting_open_mic" if mode == "live" else "greeting"
        greeting = str(self.config.get(greeting_key) or self.config.get("greeting") or "")
        greeting = greeting.replace("{ptt_key}", str(self.config.get("ptt_key", "home")))
        if greeting:
            self._speak(greeting)
        if mode == "live" and self.ptt is not None and self.record_held is not None:
            self._ptt_thread = threading.Thread(
                target=self._run_live_barge_watch,
                name="jarvis-live-barge-watch",
                daemon=True,
            )
            self._ptt_thread.start()
        self.thread = threading.Thread(target=self._run, name="jarvis-voice", daemon=True)
        self.thread.start()

    def _speak(self, text: str) -> None:
        message = str(text or "").strip()
        if not message:
            return
        now = __import__("time").monotonic()
        with self._speak_lock:
            if message == self._last_spoken_text and now - self._last_spoken_at < 1.5:
                return
            self._last_spoken_text = message
            self._last_spoken_at = now
            if self.on_output is not None:
                try:
                    self.on_output(message)
                except Exception as exc:
                    _log(f"output transcript callback error: {type(exc).__name__}: {exc}")
            if self.mouth is None:
                return
            try:
                self.mouth.say(message)
            except Exception as exc:
                _log(f"speech output error: {type(exc).__name__}: {exc}")


    def set_mouth(self, mouth: Any) -> None:
        """Atomically replace the active mouth and cancel pending audio from the old mouth."""
        if mouth is None:
            raise ValueError("mouth is required")
        with self._speak_lock:
            old = self.mouth
            if old is mouth:
                return
            self.mouth = mouth
            try:
                shut_up = getattr(old, "shut_up", None)
                if callable(shut_up):
                    shut_up()
            except Exception as exc:
                _log(f"old mouth cancellation failed: {type(exc).__name__}: {exc}")


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
        if self._mode() == "live":
            self._run_live()
        else:
            self._run_ptt()

    def set_output_active(self, active: bool) -> None:
        """Track actual WebView playback separately from TTS synthesis."""
        with self._speak_lock:
            self._browser_audio_active = bool(active)

    def _speaker_gate(self) -> bool:
        """Do not let Jarvis hear its own output; physical PTT can override."""
        speaking = bool(getattr(self.mouth, "speaking", False))
        with self._speak_lock:
            browser_audio = self._browser_audio_active
        return (speaking or browser_audio) and not self._barge_event.is_set()

    def _run_live_barge_watch(self) -> None:
        """Watch one physical key for immediate, safe barge-in and manual capture."""
        while not self.stop_event.is_set():
            try:
                self.ptt.wait_press()
                if self.stop_event.is_set():
                    break
                self._barge_event.set()
                try:
                    shut_up = getattr(self.mouth, "shut_up", None)
                    if callable(shut_up):
                        shut_up()
                except Exception as exc:
                    self._log(f"live barge-in audio cut failed: {type(exc).__name__}: {exc}")
            except Exception as exc:
                self._log(f"live barge-in watcher error: {type(exc).__name__}: {exc}")
                self.stop_event.wait(0.5)

    def _handle_live_barge(self) -> None:
        if not self._barge_event.is_set():
            return
        self._barge_event.clear()
        if self.ptt is None or self.record_held is None:
            self._log("live barge-in requested but no PTT recorder is available")
            return
        try:
            text = self.record_held(self.ptt.is_held)
            if text:
                self.handle_transcript(text)
        except Exception as exc:
            self._log(f"live barge-in capture error: {type(exc).__name__}: {exc}")

    def _run_live(self) -> None:
        """Hands-free local VAD loop with speaker gating and explicit barge-in."""
        while not self.stop_event.is_set():
            try:
                text = self.ears.listen_once(
                    gate=self._speaker_gate,
                    abort=lambda: self.stop_event.is_set() or self._barge_event.is_set(),
                    timeout_s=2.0,
                )
                if self._barge_event.is_set():
                    self._handle_live_barge()
                    continue
                if text:
                    self.handle_transcript(text)
            except Exception as exc:
                self._log(f"live-mic error: {type(exc).__name__}: {exc}")
                self.stop_event.wait(1.0)

    def _run_open_mic(self) -> None:
        """Compatibility alias for callers that explicitly request open-mic."""
        self._run_live()

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
        self.set_output_active(False)
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
        if self._ptt_thread is not None and self._ptt_thread.is_alive():
            self._ptt_thread.join(timeout=2)
        self._ptt_thread = None
        self.stopped = True
