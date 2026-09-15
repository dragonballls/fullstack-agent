import unittest
from quality_of_life.jarvis_voice import JarvisVoiceRuntime
from quality_of_life.voice_activation import VoiceActivationConfig

class NoClaudeRuntimeTests(unittest.TestCase):
    def test_jarvis_voice_brain_is_omniroute(self):
        runtime = JarvisVoiceRuntime(VoiceActivationConfig())
        self.assertEqual(runtime.brain_target.name, 'omniroute')

    def test_claude_override_is_rejected(self):
        runtime = JarvisVoiceRuntime(VoiceActivationConfig(allow_claude=True))
        with self.assertRaises(RuntimeError):
            _ = runtime.brain_target

if __name__ == '__main__':
    unittest.main()
