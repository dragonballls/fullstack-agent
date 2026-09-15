"""Local wake-word gating and single-session protection for Jarvis voice input."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
import threading
import time


@dataclass(frozen=True)
class VoiceActivationConfig:
    mode: str = "open"
    wake_word: str = "jarvis"
    wake_confidence: float = 0.70
    post_wake_window_seconds: float = 6.0
    brain: str = "omniroute"
    require_omniroute: bool = True
    allow_claude: bool = False

    @classmethod
    def from_env(cls) -> "VoiceActivationConfig":
        mode = os.environ.get("JARVIS_VOICE_MODE", "open").strip().lower()
        wake_word = os.environ.get("JARVIS_WAKE_WORD", "jarvis").strip().lower() or "jarvis"
        try:
            confidence = float(os.environ.get("JARVIS_WAKE_CONFIDENCE", "0.70"))
        except ValueError:
            confidence = 0.70
        try:
            window = float(os.environ.get("JARVIS_WAKE_POST_WINDOW_SECONDS", "6"))
        except ValueError:
            window = 6.0
        brain = os.environ.get("JARVIS_VOICE_BRAIN", "omniroute").strip().lower() or "omniroute"
        require_omniroute = os.environ.get("JARVIS_REQUIRE_OMNIROUTE", "true").strip().lower() not in {"0", "false", "no", "off"}
        return cls(
            mode=mode if mode in {"open", "ptt"} else "open",
            wake_word=wake_word,
            wake_confidence=max(0.0, min(1.0, confidence)),
            post_wake_window_seconds=max(0.0, window),
            brain=brain,
            require_omniroute=require_omniroute,
            allow_claude=False,
        )


@dataclass(frozen=True)
class WakeDecision:
    accepted: bool
    confidence: float
    phrase: str
    deadline_monotonic: float | None = None


class WakeWordGate:
    """Accept only utterances that locally contain the configured wake word."""

    def __init__(self, config: VoiceActivationConfig) -> None:
        self.config = config
        self._pattern = re.compile(rf"(?<!\w){re.escape(config.wake_word)}(?!\w)", re.IGNORECASE)

    def evaluate(self, transcript: str, confidence: float) -> WakeDecision:
        phrase = " ".join((transcript or "").split())
        score = max(0.0, min(1.0, float(confidence)))
        if not phrase or score < self.config.wake_confidence or not self._pattern.search(phrase):
            return WakeDecision(False, score, phrase)
        return WakeDecision(True, score, phrase, time.monotonic() + self.config.post_wake_window_seconds)

    @staticmethod
    def capture_expired(deadline_monotonic: float | None) -> bool:
        return deadline_monotonic is None or time.monotonic() >= deadline_monotonic


class VoiceSessionLock:
    """Prevent duplicate active voice listeners/sessions in one process."""

    _lock = threading.Lock()
    _owner = False

    def acquire(self) -> bool:
        with self._lock:
            if self._owner:
                return False
            self._owner = True
            return True

    def release(self) -> None:
        with self._lock:
            self._owner = False
