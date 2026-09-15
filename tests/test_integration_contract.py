from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IntegrationContractTests(unittest.TestCase):
    def test_installer_mentions_quality_of_life(self):
        text = (ROOT / "fullstack-agent.md").read_text(encoding="utf-8")
        self.assertIn("quality_of_life/README.md", text)
        self.assertIn("quality_of_life/manifest.py", text)
        self.assertIn("deny-by-default", text)

    def test_agent_rules_mention_quality_of_life(self):
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("quality_of_life/", text)
        self.assertIn("permission", text.lower())
        self.assertIn("self_coding", text)

    def test_installer_mentions_guarded_self_coding(self):
        text = (ROOT / "fullstack-agent.md").read_text(encoding="utf-8")
        self.assertIn("self_coding/README.md", text)
        self.assertIn("rollback", text.lower())


if __name__ == "__main__":
    unittest.main()
