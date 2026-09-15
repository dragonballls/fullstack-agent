import os
import unittest
from unittest.mock import patch

from quality_of_life.router import CloudModelRouter


class OmniRouteOnlyContractTests(unittest.TestCase):
    def test_jarvis_brain_target_is_omniroute(self):
        with patch.dict(os.environ, {}, clear=True):
            target = CloudModelRouter.jarvis_brain_target()
        self.assertEqual(target.name, "omniroute")
        self.assertEqual(target.model, "auto/smart")

    def test_claude_cannot_be_enabled_by_environment(self):
        with patch.dict(os.environ, {"JARVIS_ALLOW_CLAUDE": "true"}, clear=True):
            target = CloudModelRouter.jarvis_brain_target()
        self.assertEqual(target.name, "omniroute")

    def test_non_omniroute_brain_policy_fails_closed(self):
        with patch.dict(os.environ, {"JARVIS_VOICE_BRAIN": "claude"}, clear=True):
            with self.assertRaises(RuntimeError):
                CloudModelRouter.jarvis_brain_target()


if __name__ == "__main__":
    unittest.main()
