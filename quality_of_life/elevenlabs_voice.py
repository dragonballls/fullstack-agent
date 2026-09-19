"""First-class ElevenLabs voice engine for the Jarvis desktop host.

This module deliberately keeps the ElevenLabs API key out of source code,
process arguments, logs, and UI state. Windows installations use keyring,
which maps to the OS credential store. The WebView receives only short-lived
base64 audio packets so playback does not require a second media process.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import os
from pathlib import Path
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from typing import Any


SERVICE_NAME = "Jarvis"
ACCOUNT_NAME = "ElevenLabs"
API_BASE = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # ElevenLabs public example voice: George
DEFAULT_MODEL_ID = "eleven_flash_v2_5"
EXPRESSIVE_MODEL_ID = "eleven_v3"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
CONFIG_DIR = Path.home() / "AppData" / "Local" / "Jarvis" / "settings"
CONFIG_FILE = CONFIG_DIR / "elevenlabs.json"
MAX_TEXT = 12000


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _keyring_module() -> Any:
    try:
        import keyring
    except ImportError as exc:
        raise RuntimeError("keyring is required for ElevenLabs credential storage") from exc
    return keyring


def _redact_error(message: str, secret: str = "") -> str:
    text = str(message or "")
    secrets = {
        os.environ.get("ELEVENLABS_API_KEY", "").strip(),
        str(secret or "").strip(),
    }
    for value in secrets:
        if value:
            text = text.replace(value, "[redacted]")
    return text[:500]


def _load_settings() -> dict[str, str]:
    try:
        payload = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    model = str(payload.get("model_id") or DEFAULT_MODEL_ID).strip()
    if model not in {DEFAULT_MODEL_ID, EXPRESSIVE_MODEL_ID}:
        model = DEFAULT_MODEL_ID
    voice_id = str(payload.get("voice_id") or DEFAULT_VOICE_ID).strip()
    return {"voice_id": voice_id[:256], "model_id": model}


def _save_settings(settings: dict[str, str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    temporary.replace(CONFIG_FILE)


def get_api_key() -> str:
    override = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if override:
        return override
    try:
        value = _keyring_module().get_password(SERVICE_NAME, ACCOUNT_NAME)
    except Exception:
        return ""
    return str(value or "").strip()


def has_api_key() -> bool:
    return bool(get_api_key())


def save_api_key(api_key: str) -> None:
    key = str(api_key or "").strip()
    if len(key) < 8:
        raise ValueError("ElevenLabs API key is too short")
    try:
        _keyring_module().set_password(SERVICE_NAME, ACCOUNT_NAME, key)
    except Exception as exc:
        raise RuntimeError("Windows credential storage is unavailable") from exc


def clear_api_key() -> None:
    try:
        _keyring_module().delete_password(SERVICE_NAME, ACCOUNT_NAME)
    except Exception:
        pass


def decorate_for_jarvis(text: str, model_id: str) -> str:
    """Add sparse delivery guidance without changing the user's words."""
    message = str(text or "").strip()
    if not message or model_id != EXPRESSIVE_MODEL_ID:
        return message
    lowered = message.lower()
    if message.endswith("?"):
        return "[curious] " + message
    if any(token in lowered for token in ("i found", "i've completed", "completed", "ready", "done")):
        return "[confident] " + message
    if "!" in message:
        return "[excited] " + message
    if any(token in lowered for token in ("one moment", "let me think", "checking", "analyzing")):
        return "[thoughtful] " + message
    return message


@dataclass(frozen=True)
class VoiceAudioPacket:
    sequence: int
    mime: str
    data: str


class ElevenLabsClient:
    """Small dependency-light client for the current ElevenLabs speech API."""

    def __init__(self, *, api_base: str = API_BASE, timeout_seconds: float = 45.0) -> None:
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = max(5.0, float(timeout_seconds))

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, bytes, dict[str, str]]:
        key = get_api_key()
        if not key:
            raise RuntimeError("ElevenLabs API key is not configured")
        request_headers = {
            "Accept": "application/json",
            "xi-api-key": key,
        }
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(
            self.api_base + path,
            data=body,
            headers=request_headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return int(response.status), response.read(), dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            payload = exc.read(512)
            detail = payload.decode("utf-8", "replace").strip()
            raise RuntimeError(f"ElevenLabs request failed with HTTP {exc.code}: {_redact_error(detail, key)}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError("ElevenLabs connection failed") from exc

    def test_connection(self) -> dict[str, object]:
        status, _body, _headers = self._request("GET", "/models")
        return {"ok": 200 <= status < 300, "tested": True, "message": "ElevenLabs connection passed"}

    def list_voices(self) -> list[dict[str, str]]:
        status, body, _headers = self._request("GET", "/voices")
        if not 200 <= status < 300:
            return []
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return []
        result: list[dict[str, str]] = []
        for voice in payload.get("voices", []) if isinstance(payload, dict) else []:
            if not isinstance(voice, dict):
                continue
            voice_id = str(voice.get("voice_id") or "").strip()
            name = str(voice.get("name") or voice_id).strip()
            if voice_id:
                result.append({"id": voice_id[:256], "name": name[:256]})
        return result

    def synthesize(
        self,
        text: str,
        *,
        voice_id: str,
        model_id: str,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
    ) -> bytes:
        message = decorate_for_jarvis(text, model_id)
        if not message:
            return b""
        if len(message) > MAX_TEXT:
            message = message[:MAX_TEXT]
        query = urllib.parse.urlencode({"output_format": output_format})
        body = json.dumps(
            {
                "text": message,
                "model_id": model_id,
                "voice_settings": {
                    "stability": 0.55,
                    "similarity_boost": 0.88,
                    "style": 0.05,
                    "use_speaker_boost": True,
                    "speed": 0.98,
                },
            }
        ).encode("utf-8")
        status, audio, _headers = self._request(
            "POST",
            f"/text-to-speech/{urllib.parse.quote(voice_id, safe='')}/stream?{query}",
            body=body,
            headers={"Content-Type": "application/json", "Accept": "audio/mpeg"},
        )
        if not 200 <= status < 300 or not audio:
            raise RuntimeError("ElevenLabs returned no playable audio")
        return audio


class ElevenLabsMouth:
    """Non-blocking Jarvis mouth that emits browser-playable audio packets."""

    def __init__(self, client: ElevenLabsClient | None = None) -> None:
        self.client = client or ElevenLabsClient()
        settings = _load_settings()
        self.voice_id = settings["voice_id"]
        self.model_id = settings["model_id"]
        self._lock = threading.RLock()
        self._generation = 0
        self._queue: deque[VoiceAudioPacket] = deque(maxlen=4)
        self._workers: set[threading.Thread] = set()
        self._speaking = False
        self._last_error = ""
        self._configured_at = time.monotonic()

    @property
    def speaking(self) -> bool:
        with self._lock:
            return self._speaking

    @property
    def configured(self) -> bool:
        return has_api_key()

    def configure(self, api_key: str, *, voice_id: str | None = None, model_id: str | None = None) -> dict[str, object]:
        save_api_key(api_key)
        selected_voice = str(voice_id or self.voice_id or DEFAULT_VOICE_ID).strip()[:256]
        selected_model = str(model_id or self.model_id or DEFAULT_MODEL_ID).strip()
        if selected_model not in {DEFAULT_MODEL_ID, EXPRESSIVE_MODEL_ID}:
            raise ValueError("unsupported ElevenLabs model")
        _save_settings({"voice_id": selected_voice, "model_id": selected_model})
        with self._lock:
            self.voice_id = selected_voice
            self.model_id = selected_model
            self._last_error = ""
        return {
            "ok": True,
            "configured": True,
            "voice_id": self.voice_id,
            "model_id": self.model_id,
        }

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "ok": True,
                "configured": self.configured,
                "provider": "ElevenLabs",
                "voice_id": self.voice_id,
                "model_id": self.model_id,
                "speaking": self._speaking,
                "last_error": self._last_error,
            }

    def test(self) -> dict[str, object]:
        if not self.configured:
            return {
                "ok": False,
                "configured": False,
                "tested": False,
                "message": "ElevenLabs API key is not configured",
            }
        try:
            result = self.client.test_connection()
            with self._lock:
                self._last_error = "" if result.get("ok") else str(result.get("message", "connection test failed"))
            return result
        except Exception as exc:
            with self._lock:
                self._last_error = _redact_error(exc, get_api_key())
            return {"ok": False, "configured": True, "tested": True, "message": "ElevenLabs connection test failed"}

    def test_speech(self, text: str = "Voice channel confirmed.") -> dict[str, object]:
        if not self.configured:
            return {
                "ok": False,
                "configured": False,
                "tested": False,
                "message": "ElevenLabs API key is not configured",
            }
        try:
            with self._lock:
                self._generation += 1
                generation = self._generation
                voice_id, model_id = self.voice_id, self.model_id
            audio = self.client.synthesize(text, voice_id=voice_id, model_id=model_id)
            with self._lock:
                if generation == self._generation:
                    self._queue.append(
                        VoiceAudioPacket(
                            sequence=generation,
                            mime="audio/mpeg",
                            data=base64.b64encode(audio).decode("ascii"),
                        )
                    )
                    self._last_error = ""
            return {"ok": True, "configured": True, "tested": True, "spoken": True, "message": "ElevenLabs speech test passed"}
        except Exception as exc:
            with self._lock:
                self._last_error = _redact_error(exc)
            return {"ok": False, "configured": True, "tested": True, "spoken": False, "message": "ElevenLabs speech test failed"}

    def say(self, text: str) -> None:
        message = str(text or "").strip()
        if not message or not self.configured:
            return
        with self._lock:
            self._generation += 1
            generation = self._generation
            self._speaking = True
            self._last_error = ""
        worker = threading.Thread(
            target=self._synthesize_worker,
            args=(message, generation),
            name="jarvis-elevenlabs-tts",
            daemon=True,
        )
        with self._lock:
            self._workers.add(worker)
        worker.start()

    def _synthesize_worker(self, message: str, generation: int) -> None:
        current = threading.current_thread()
        try:
            with self._lock:
                voice_id, model_id = self.voice_id, self.model_id
            audio = self.client.synthesize(message, voice_id=voice_id, model_id=model_id)
            with self._lock:
                if generation != self._generation:
                    return
                self._queue.append(
                    VoiceAudioPacket(
                        sequence=generation,
                        mime="audio/mpeg",
                        data=base64.b64encode(audio).decode("ascii"),
                    )
                )
        except Exception as exc:
            with self._lock:
                if generation == self._generation:
                    self._last_error = _redact_error(exc)
        finally:
            with self._lock:
                self._workers.discard(current)
                if generation == self._generation:
                    self._speaking = False

    def take_audio(self) -> list[dict[str, object]]:
        with self._lock:
            packets = list(self._queue)
            self._queue.clear()
        return [
            {"sequence": item.sequence, "mime": item.mime, "data": item.data}
            for item in packets
        ]

    def shut_up(self) -> None:
        with self._lock:
            self._generation += 1
            self._queue.clear()
            self._speaking = False

    def shutdown(self) -> None:
        self.shut_up()
        for worker in list(self._workers):
            if worker.is_alive():
                worker.join(timeout=0.5)
        with self._lock:
            self._workers.clear()
