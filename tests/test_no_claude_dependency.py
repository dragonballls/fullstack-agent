from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NoClaudeDependencyTests(unittest.TestCase):
    def test_required_contracts_do_not_require_claude(self):
        required_files = ["README.md", "fullstack-agent.md", "JARVIS_READINESS.md", "JARVIS_ORCHESTRATION.md"]
        forbidden = ["You need Claude Code", "Claude subscription", 'claude "set me up"']
        for name in required_files:
            text = (ROOT / name).read_text(encoding="utf-8")
            for phrase in forbidden:
                self.assertNotIn(phrase, text, f"{name} still requires Claude: {phrase}")

    def test_required_contracts_identify_omniroute(self):
        for name in ["README.md", "JARVIS_READINESS.md", "JARVIS_ORCHESTRATION.md"]:
            text = (ROOT / name).read_text(encoding="utf-8").lower()
            self.assertIn("omniroute", text, name)


if __name__ == "__main__":
    unittest.main()
