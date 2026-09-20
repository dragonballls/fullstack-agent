import base64
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from quality_of_life.elevenlabs_voice import KokoroMouth


class _FakePipeline:
    def __call__(self, text, *, voice, speed):
        del text, voice, speed
        yield SimpleNamespace(audio=[0.0, 0.25, -0.25, 0.0])


class KokoroMouthTests(TestCase):
    def test_kokoro_voice_queues_playable_wav_packet(self):
        mouth = KokoroMouth(pipeline=_FakePipeline())
        result = mouth.test_speech("hello")
        self.assertTrue(result["ok"])
        packets = mouth.take_audio()
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0]["mime"], "audio/wav")
        self.assertTrue(base64.b64decode(packets[0]["data"]).startswith(b"RIFF"))

    def test_new_generation_cancels_older_audio(self):
        mouth = KokoroMouth(pipeline=_FakePipeline())
        mouth._generation = 7
        mouth.say("first")
        first_generation = mouth.generation
        mouth.shut_up()
        cancelled_generation = mouth.generation
        mouth._run_generation("stale", first_generation)
        self.assertEqual(mouth.take_audio(), [])
        self.assertEqual(mouth.generation, cancelled_generation)

    def test_missing_kokoro_is_reported_without_startup_import_failure(self):
        mouth = KokoroMouth(pipeline=None)
        with patch.dict("sys.modules", {"kokoro": None}):
            self.assertFalse(mouth.available())
