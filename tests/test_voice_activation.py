import os
import unittest
from unittest.mock import patch

from quality_of_life.voice_activation import VoiceActivationConfig, VoiceSessionLock, WakeWordGate


class VoiceActivationTests(unittest.TestCase):
    def test_defaults_are_always_listening_and_jarvis(self):
        with patch.dict(os.environ, {}, clear=True):
            config = VoiceActivationConfig.from_env()
        self.assertEqual(config.mode, "open")
        self.assertEqual(config.wake_word, "jarvis")
        self.assertAlmostEqual(config.wake_confidence, 0.70)
        self.assertEqual(config.post_wake_window_seconds, 6.0)
        self.assertEqual(config.brain, "omniroute")
        self.assertTrue(config.require_omniroute)
        self.assertFalse(config.allow_claude)

    def test_wake_word_requires_boundary_and_confidence(self):
        gate = WakeWordGate(VoiceActivationConfig())
        self.assertTrue(gate.evaluate("Jarvis, open Opera", 0.90).accepted)
        self.assertTrue(gate.evaluate("please JARVIS", 0.70).accepted)
        self.assertFalse(gate.evaluate("jarvisness is not an address", 0.99).accepted)
        self.assertFalse(gate.evaluate("Jarvis open Opera", 0.69).accepted)

    def test_rejects_non_addressed_speech(self):
        gate = WakeWordGate(VoiceActivationConfig())
        self.assertFalse(gate.evaluate("hello everyone", 0.99).accepted)
        self.assertFalse(gate.evaluate("", 1.0).accepted)

    def test_post_wake_capture_expires(self):
        config = VoiceActivationConfig(post_wake_window_seconds=0.0)
        decision = WakeWordGate(config).evaluate("Jarvis", 1.0)
        self.assertTrue(decision.accepted)
        self.assertTrue(WakeWordGate.capture_expired(decision.deadline_monotonic))

    def test_duplicate_listeners_are_blocked(self):
        lock = VoiceSessionLock()
        self.assertTrue(lock.acquire())
        self.assertFalse(lock.acquire())
        lock.release()
        self.assertTrue(lock.acquire())
        lock.release()


if __name__ == "__main__":
    unittest.main()
