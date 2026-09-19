from __future__ import annotations

import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from quality_of_life.elevenlabs_voice import (
    DEFAULT_MODEL_ID,
    DEFAULT_VOICE_ID,
    EXPRESSIVE_MODEL_ID,
    LOW_LATENCY_MODEL_ID,
    ElevenLabsClient,
    ElevenLabsMouth,
    decorate_for_jarvis,
)


class ElevenLabsVoiceTests(unittest.TestCase):
    def test_defaults_target_low_latency_conversation(self):
        self.assertEqual(DEFAULT_MODEL_ID, "eleven_v3_conversational")
        self.assertEqual(LOW_LATENCY_MODEL_ID, "eleven_flash_v2_5")
        self.assertTrue(DEFAULT_VOICE_ID)

    def test_v3_delivery_guidance_is_sparse_and_preserves_dialogue(self):
        source = "I've completed the diagnostics."
        decorated = decorate_for_jarvis(source, EXPRESSIVE_MODEL_ID)
        self.assertTrue(decorated.startswith("[confident] "))
        self.assertTrue(decorated.endswith(source))
        self.assertTrue(decorate_for_jarvis(source, DEFAULT_MODEL_ID).startswith("[confident] "))

    def test_client_sends_key_only_as_xi_api_key_header(self):
        client = ElevenLabsClient()
        secret = "eleven-secret-123456"
        with patch("quality_of_life.elevenlabs_voice.get_api_key", return_value=secret), patch(
            "urllib.request.urlopen"
        ) as urlopen:
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.status = 200
            response.read.return_value = b"MP3"
            urlopen.return_value = response
            audio = client.synthesize("Hello", voice_id="voice-1", model_id=DEFAULT_MODEL_ID)
        self.assertEqual(audio, b"MP3")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Xi-api-key"), secret)
        self.assertNotIn(secret, request.full_url)
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["text"], "Hello")
        self.assertEqual(payload["model_id"], DEFAULT_MODEL_ID)

    def test_mouth_queues_base64_audio_and_does_not_leak_key(self):
        mouth = ElevenLabsMouth(client=Mock())
        mouth.client.synthesize.return_value = b"fake-mp3"
        with patch("quality_of_life.elevenlabs_voice.has_api_key", return_value=True):
            mouth.say("Hello Jarvis")
            deadline = __import__("time").monotonic() + 2
            while not mouth._workers and __import__("time").monotonic() < deadline:
                __import__("time").sleep(0.01)
            for worker in list(mouth._workers):
                worker.join(timeout=2)
        packets = mouth.take_audio()
        self.assertEqual(len(packets), 1)
        self.assertEqual(base64.b64decode(packets[0]["data"]), b"fake-mp3")
        self.assertNotIn("fake", repr(packets))

    def test_speech_test_generates_real_audio_packet(self):
        mouth = ElevenLabsMouth(client=Mock())
        mouth.client.synthesize.return_value = b"test-mp3"
        with patch("quality_of_life.elevenlabs_voice.has_api_key", return_value=True):
            result = mouth.test_speech()
        self.assertTrue(result["ok"])
        self.assertTrue(result["spoken"])
        packets = mouth.take_audio()
        self.assertEqual(base64.b64decode(packets[0]["data"]), b"test-mp3")

    def test_status_is_credential_free(self):
        mouth = ElevenLabsMouth(client=Mock())
        with patch("quality_of_life.elevenlabs_voice.has_api_key", return_value=True):
            status = mouth.status()
        self.assertNotIn("api_key", repr(status))
        self.assertNotIn("secret", repr(status).lower())

    def test_stale_generation_is_dropped_after_shut_up(self):
        mouth = ElevenLabsMouth(client=Mock())
        started = Mock()
        def synth(*args, **kwargs):
            started.set()
            return b"late-audio"
        mouth.client.synthesize.side_effect = synth
        with patch("quality_of_life.elevenlabs_voice.has_api_key", return_value=True):
            mouth.say("stop this")
            started.wait(timeout=2)
            mouth.shut_up()
            for worker in list(mouth._workers):
                worker.join(timeout=2)
        self.assertEqual(mouth.take_audio(), [])

    def test_first_setup_prefers_current_british_voice_when_available(self):
        client = Mock()
        client.list_voices.return_value = [{"id": "current-british-id", "name": "Eldrin"}]
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "elevenlabs.json"
            fake_keyring = Mock()
            with patch("quality_of_life.elevenlabs_voice._keyring_module", return_value=fake_keyring), patch(
                "quality_of_life.elevenlabs_voice.CONFIG_FILE", config
            ), patch("quality_of_life.elevenlabs_voice.CONFIG_DIR", Path(temp)):
                mouth = ElevenLabsMouth(client=client)
                result = mouth.configure("test-secret-123456")
        self.assertEqual(result["voice_id"], "current-british-id")

    def test_configure_uses_credential_store_and_writes_only_nonsecret_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "elevenlabs.json"
            fake_keyring = Mock()
            with patch("quality_of_life.elevenlabs_voice._keyring_module", return_value=fake_keyring), patch(
                "quality_of_life.elevenlabs_voice.CONFIG_FILE", config
            ), patch("quality_of_life.elevenlabs_voice.CONFIG_DIR", Path(temp)):
                mouth = ElevenLabsMouth(client=Mock())
                result = mouth.configure("test-secret-123456", voice_id="voice-x", model_id=EXPRESSIVE_MODEL_ID)
            fake_keyring.set_password.assert_called_once_with("Jarvis", "ElevenLabs", "test-secret-123456")
            self.assertEqual(result["voice_id"], "voice-x")
            self.assertNotIn("test-secret-123456", config.read_text(encoding="utf-8"))
            self.assertIn("voice-x", config.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
