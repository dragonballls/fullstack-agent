"""Optional local always-listening microphone listener for Jarvis."""

from __future__ import annotations

from collections.abc import Callable
import importlib
import threading
import time
from dataclasses import dataclass
from typing import Any


class VoiceListenerUnavailable(RuntimeError):
    """Raised when optional microphone/wake-word dependencies are unavailable."""


@dataclass(frozen=True)
class WakeEvent:
    model: str
    confidence: float


class LocalWakeWordListener:
    """Listen locally for a wake word and invoke a callback without cloud access."""

    def __init__(self, *, model_name: str = "hey_jarvis", threshold: float = 0.70, sample_rate: int = 16000, block_size: int = 1280, cooldown_seconds: float = 2.0, on_wake: Callable[[WakeEvent], None] | None = None, sounddevice_module: Any | None = None, wakeword_model: Any | None = None) -> None:
        self.model_name = model_name
        self.threshold = max(0.0, min(1.0, threshold))
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.cooldown_seconds = max(0.0, cooldown_seconds)
        self.on_wake = on_wake
        self._sounddevice = sounddevice_module
        self._wakeword_model = wakeword_model
        self._activation_lock = threading.Lock()
        self._last_activation = 0.0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._state_lock = threading.Lock()
        self._last_error: str | None = None

    @property
    def running(self) -> bool:
        with self._state_lock:
            return self._thread is not None and self._thread.is_alive()

    @property
    def last_error(self) -> str | None:
        with self._state_lock:
            return self._last_error

    def _load_dependencies(self) -> tuple[Any, Any]:
        sounddevice = self._sounddevice
        model = self._wakeword_model
        if sounddevice is None:
            try:
                sounddevice = importlib.import_module("sounddevice")
            except ImportError as exc:
                raise VoiceListenerUnavailable("sounddevice is not installed") from exc
        if model is None:
            try:
                importlib.import_module("openwakeword")
                model_cls = importlib.import_module("openwakeword.model").Model
                model = model_cls(wakeword_models=[self.model_name])
            except ImportError as exc:
                raise VoiceListenerUnavailable("openwakeword is not installed") from exc
        return sounddevice, model

    @staticmethod
    def _score(prediction: dict[str, float], model_name: str) -> float:
        if model_name in prediction:
            return float(prediction[model_name])
        matching = [float(value) for name, value in prediction.items() if model_name in name]
        return max(matching, default=0.0)

    def _emit_wake(self, score: float) -> None:
        if self.on_wake is None:
            return
        now = time.monotonic()
        with self._activation_lock:
            if now - self._last_activation < self.cooldown_seconds:
                return
            self._last_activation = now
        self.on_wake(WakeEvent(self.model_name, score))

    def process_prediction(self, prediction: dict[str, float]) -> None:
        """Process one local wake-model prediction without making a network request."""
        score = self._score(prediction, self.model_name)
        if score >= self.threshold:
            self._emit_wake(score)

    def start(self) -> bool:
        """Start one daemon listener thread; repeated starts are idempotent."""
        with self._state_lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self._stop_event.clear()
            self._last_error = None
            self._thread = threading.Thread(target=self._run_thread, name="jarvis-wake-listener", daemon=True)
            self._thread.start()
            return True

    def stop(self) -> None:
        """Request shutdown and join the listener thread."""
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        with self._state_lock:
            if self._thread is thread and (thread is None or not thread.is_alive()):
                self._thread = None

    def _run_thread(self) -> None:
        try:
            self.run_forever()
        except Exception as exc:  # noqa: BLE001
            with self._state_lock:
                self._last_error = str(exc)

    def run_forever(self) -> None:
        """Continuously monitor the local microphone; no network call is made here."""
        sounddevice, model = self._load_dependencies()

        def callback(indata: Any, _frames: int, _stream_time: Any, _status: Any) -> None:
            audio = (indata.reshape(-1) * 32767).astype("int16")
            self.process_prediction(model.predict(audio))

        self._stop_event.clear()
        with sounddevice.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32", blocksize=self.block_size, callback=callback):
            while not self._stop_event.wait(0.5):
                pass
