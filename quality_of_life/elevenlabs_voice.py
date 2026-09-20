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
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # compatibility fallback; first-time setup prefers a current voice
DEFAULT_PREFERRED_VOICE_NAME = "Eldrin"
DEFAULT_MODEL_ID = "eleven_v3_conversational"
LOW_LATENCY_MODEL_ID = "eleven_flash_v2_5"
EXPRESSIVE_MODEL_ID = "eleven_v3"
SUPPORTED_MODEL_IDS = {DEFAULT_MODEL_ID, LOW_LATENCY_MODEL_ID, EXPRESSIVE_MODEL_ID}
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
    if model not in SUPPORTED_MODEL_IDS:
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
    ) -> tuple[int, bytes]:
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
                return int(response.status), response.read()
        except urllib.error.HTTPError as exc:
            payload = exc.read(512)
            detail = payload.decode("utf-8", "replace").strip()
            raise RuntimeError(f"ElevenLabs request failed with HTTP {exc.code}: {_redact_error(detail, key)}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError("ElevenLabs connection failed") from exc

    def test_connection(self) -> dict[str, object]:
        status, _body = self._request("GET", "/models")
        return {"ok": 200 <= status < 300, "tested": True, "message": "ElevenLabs connection passed"}

    def list_voices(self) -> list[dict[str, str]]:
        status, body = self._request("GET", "/voices")
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
        status, audio = self._request(
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
    def generation(self) -> int:
        with self._lock:
            return self._generation

    @property
    def speaking(self) -> bool:
        with self._lock:
            return self._speaking

    @property
    def configured(self) -> bool:
        return has_api_key()

    def configure(self, api_key: str, *, voice_id: str | None = None, model_id: str | None = None) -> dict[str, object]:
        save_api_key(api_key)
        explicit_voice = str(voice_id or "").strip()
        selected_voice = explicit_voice or self.voice_id or DEFAULT_VOICE_ID
        if not explicit_voice and selected_voice == DEFAULT_VOICE_ID:
            try:
                for voice in self.client.list_voices():
                    if str(voice.get("name", "")).strip().casefold() == DEFAULT_PREFERRED_VOICE_NAME.casefold():
                        selected_voice = str(voice.get("id", "")).strip() or selected_voice
                        break
            except Exception:
                pass
        selected_voice = str(selected_voice).strip()[:256]
        selected_model = str(model_id or self.model_id or DEFAULT_MODEL_ID).strip()
        if selected_model not in SUPPORTED_MODEL_IDS:
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
        with self._lock:
            workers = list(self._workers)
        for worker in workers:
            if worker.is_alive():
                worker.join(timeout=0.5)
        with self._lock:
            self._workers.clear()


FREE_VOICE_PROVIDER = "kokoro"
KOKORO_DEFAULT_VOICE = "bm_lewis"
KOKORO_LANG_CODE = "b"
KOKORO_MODEL_ID = "hexgrad/Kokoro-82M"
KOKORO_SAMPLE_RATE = 24000


class KokoroMouth:
    """Local, zero-cost TTS mouth with cancellable generation and streamed packets."""

    def __init__(
        self,
        *,
        voice_id: str | None = None,
        device: str | None = None,
        speed: float = 1.0,
        pipeline: Any | None = None,
    ) -> None:
        self.voice_id = (voice_id or os.environ.get("JARVIS_KOKORO_VOICE") or KOKORO_DEFAULT_VOICE).strip()[:128]
        self.device = (device or os.environ.get("JARVIS_KOKORO_DEVICE") or "cpu").strip().lower()
        self.speed = min(2.0, max(0.65, float(speed)))
        self._pipeline = pipeline
        self._pipeline_lock = threading.RLock()
        self._lock = threading.RLock()
        self._generation = 0
        self._queue: deque[VoiceAudioPacket] = deque(maxlen=24)
        self._workers: set[threading.Thread] = set()
        self._speaking = False
        self._prepared = pipeline is not None
        self._last_error = ""

    @staticmethod
    def available() -> bool:
        try:
            import kokoro  # noqa: F401
            return True
        except Exception:
            return False

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

    @property
    def speaking(self) -> bool:
        with self._lock:
            return self._speaking

    @property
    def configured(self) -> bool:
        return self.available()

    @property
    def prepared(self) -> bool:
        with self._lock:
            return self._prepared

    def _get_pipeline(self) -> Any:
        with self._pipeline_lock:
            if self._pipeline is not None:
                return self._pipeline
            try:
                from kokoro import KPipeline
                self._pipeline = KPipeline(lang_code=KOKORO_LANG_CODE, device=self.device)
            except Exception as exc:
                with self._lock:
                    self._last_error = _redact_error(exc)
                raise RuntimeError("Local Kokoro voice engine could not initialize") from exc
            return self._pipeline

    def prepare(self) -> dict[str, object]:
        pipeline = self._get_pipeline()
        try:
            loader = getattr(pipeline, "load_voice", None)
            if callable(loader):
                loader(self.voice_id)
            with self._lock:
                self._prepared = True
                self._last_error = ""
            return {
                "ok": True,
                "provider": "Kokoro Local",
                "voice_id": self.voice_id,
                "model_id": KOKORO_MODEL_ID,
                "prepared": True,
            }
        except Exception as exc:
            with self._lock:
                self._last_error = _redact_error(exc)
            raise RuntimeError("Local Kokoro voice preparation failed") from exc

    @staticmethod
    def _wav_bytes(audio: Any) -> bytes:
        """Encode Kokoro audio without requiring NumPy in the regression/runtime layer."""
        import array
        import io
        import math
        import wave

        value = audio
        for name in ("detach", "cpu", "numpy", "flatten"):
            method = getattr(value, name, None)
            if callable(method):
                try:
                    value = method()
                except TypeError:
                    continue
        tolist = getattr(value, "tolist", None)
        if callable(tolist):
            value = tolist()
        if isinstance(value, (tuple, list)):
            values = value
        else:
            try:
                values = list(value)
            except TypeError:
                values = [value]
        while values and isinstance(values[0], (tuple, list)):
            flattened = []
            for row in values:
                flattened.extend(row if isinstance(row, (tuple, list)) else [row])
            values = flattened

        pcm = array.array("h")
        for sample in values:
            try:
                numeric = float(sample)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(numeric):
                numeric = 0.0
            numeric = max(-1.0, min(1.0, numeric))
            pcm.append(int(round(numeric * 32767.0)))

        if not pcm:
            return b""
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(KOKORO_SAMPLE_RATE)
            wav.writeframes(pcm.tobytes())
        return output.getvalue()

    def _run_generation(self, message: str, generation: int) -> None:
        pipeline = self._get_pipeline()
        with self._pipeline_lock:
            generator = pipeline(message, voice=self.voice_id, speed=self.speed)
            for result in generator:
                audio = getattr(result, "audio", None)
                if audio is None:
                    try:
                        audio = result[2]
                    except Exception:
                        audio = None
                if audio is None:
                    continue
                packet_data = self._wav_bytes(audio)
                if not packet_data:
                    continue
                with self._lock:
                    if generation != self._generation:
                        return
                    self._queue.append(
                        VoiceAudioPacket(
                            sequence=generation,
                            mime="audio/wav",
                            data=base64.b64encode(packet_data).decode("ascii"),
                        )
                    )
                    self._prepared = True
        with self._lock:
            if generation == self._generation:
                self._last_error = ""

    def say(self, text: str) -> None:
        message = str(text or "").strip()
        if not message:
            return
        with self._lock:
            self._generation += 1
            generation = self._generation
            self._speaking = True
            self._last_error = ""
        worker = threading.Thread(
            target=self._worker,
            args=(message, generation),
            name="jarvis-kokoro-tts",
            daemon=True,
        )
        with self._lock:
            self._workers.add(worker)
        worker.start()

    def _worker(self, message: str, generation: int) -> None:
        current = threading.current_thread()
        try:
            self._run_generation(message, generation)
        except Exception as exc:
            with self._lock:
                if generation == self._generation:
                    self._last_error = _redact_error(exc)
        finally:
            with self._lock:
                self._workers.discard(current)
                if generation == self._generation:
                    self._speaking = False

    def test_speech(self, text: str = "Local voice channel confirmed.") -> dict[str, object]:
        try:
            with self._lock:
                self._generation += 1
                generation = self._generation
                self._speaking = True
                self._last_error = ""
            self._run_generation(text, generation)
            with self._lock:
                spoken = any(packet.sequence == generation for packet in self._queue)
                if generation == self._generation:
                    self._speaking = False
            return {
                "ok": spoken,
                "configured": self.configured,
                "tested": True,
                "spoken": spoken,
                "provider": "Kokoro Local",
                "message": "Local Kokoro speech test passed" if spoken else "Local Kokoro speech test produced no audio",
            }
        except Exception:
            with self._lock:
                self._speaking = False
                self._last_error = "Local Kokoro speech test failed"
            return {
                "ok": False,
                "configured": self.configured,
                "tested": True,
                "spoken": False,
                "provider": "Kokoro Local",
                "message": "Local Kokoro speech test failed",
            }

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "ok": True,
                "configured": self.configured,
                "provider": "Kokoro Local",
                "voice_id": self.voice_id,
                "model_id": KOKORO_MODEL_ID,
                "device": self.device,
                "prepared": self._prepared,
                "speaking": self._speaking,
                "generation": self._generation,
                "last_error": self._last_error,
            }

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
        with self._lock:
            workers = list(self._workers)
        for worker in workers:
            if worker.is_alive():
                worker.join(timeout=0.7)
        with self._lock:
            self._workers.clear()

    def warm_up(self) -> dict[str, object]:
        return self.prepare()
