from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SingleExeContractTests(unittest.TestCase):
    def test_desktop_host_is_not_the_obsolete_tk_chat_bar(self):
        text = (ROOT / "scripts/jarvis_desktop.py").read_text(encoding="utf-8")
        self.assertNotIn('self.root.geometry("640x118")', text)
        self.assertNotIn('value="Jarvis is ready."', text)
        self.assertIn("Fullstack", text)

    def test_release_workflow_mentions_embedded_fullstack_components(self):
        text = (ROOT / ".github/workflows/jarvis-release-gate.yml").read_text(encoding="utf-8")
        self.assertIn("Jarvis.exe", text)
        self.assertIn("jaredrhod/ai-visualizer", text)
        self.assertIn("jaredrhod/backtalk", text)
        self.assertIn("jaredrhod/barehands", text)


if __name__ == "__main__":
    unittest.main()
