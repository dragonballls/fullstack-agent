import unittest
from unittest.mock import patch

from quality_of_life.jarvis_voice import JarvisVoiceRuntime
from quality_of_life.voice_activation import VoiceActivationConfig


class JarvisVoiceRuntimeTests(unittest.TestCase):
    def test_non_addressed_speech_never_routes(self):
        runtime = JarvisVoiceRuntime(VoiceActivationConfig())
        result = runtime.route("hello everyone", 0.99)
        self.assertFalse(result.decision.accepted)
        self.assertIsNone(result.response)
        self.assertIsNone(result.provider)

    def test_brain_target_is_omniroute(self):
        runtime = JarvisVoiceRuntime(VoiceActivationConfig())
        self.assertEqual(runtime.brain_target.name, "omniroute")

    def test_claude_policy_fails_closed(self):
        runtime = JarvisVoiceRuntime(VoiceActivationConfig(allow_claude=True))
        with self.assertRaises(RuntimeError):
            _ = runtime.brain_target

    @patch("quality_of_life.jarvis_voice.CloudModelRouter.complete")
    def test_accepted_speech_is_sent_through_existing_router(self, complete):
        complete.return_value = ("Ready.", "omniroute")
        runtime = JarvisVoiceRuntime(VoiceActivationConfig())
        result = runtime.route("Jarvis open Opera", 0.99)
        self.assertTrue(result.decision.accepted)
        self.assertEqual(result.response, "Ready.")
        self.assertEqual(result.provider, "omniroute")
        complete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
