from __future__ import annotations

import unittest

from setup_elevenlabs import PREFERRED_VOICE, choose_voice


class ElevenLabsSetupTests(unittest.TestCase):
    def test_prefers_tarquin_when_available(self) -> None:
        voices = [
            {"voice_id": "other", "name": "Other", "labels": {"accent": "British", "gender": "male"}},
            {"voice_id": "tarquin-id", "name": PREFERRED_VOICE, "labels": {}},
        ]
        selected = choose_voice(voices)
        self.assertEqual(selected["voice_id"], "tarquin-id")

    def test_uses_metadata_fallback_without_guessing_an_id(self) -> None:
        voices = [
            {
                "voice_id": "british-male",
                "name": "British Professional",
                "labels": {"accent": "British", "gender": "male"},
                "description": "Calm professional voice",
            },
            {
                "voice_id": "american-male",
                "name": "American Casual",
                "labels": {"accent": "American", "gender": "male"},
                "description": "Friendly casual voice",
            },
        ]
        selected = choose_voice(voices)
        self.assertEqual(selected["voice_id"], "british-male")

    def test_fails_when_no_voices_are_available(self) -> None:
        with self.assertRaises(RuntimeError):
            choose_voice([])


if __name__ == "__main__":
    unittest.main()
