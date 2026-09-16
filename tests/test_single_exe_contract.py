from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SingleExeContractTests(unittest.TestCase):
    def test_desktop_host_is_not_the_obsolete_tk_chat_bar(self):
        text = (ROOT / "scripts/jarvis_desktop.py").read_text(encoding="utf-8")
        self.assertNotIn('self.root.geometry("640x118")', text)
        self.assertNotIn('value="Jarvis is ready."', text)
        self.assertIn("Fullstack", text)
        self.assertIn("VisualizerAdapter", text)
        self.assertIn("VoiceAdapter", text)

    def test_release_workflow_builds_and_publishes_a_raw_exe(self):
        text = (ROOT / ".github/workflows/jarvis-release-gate.yml").read_text(encoding="utf-8")
        self.assertIn("scripts/fetch-fullstack-components.py", text)
        self.assertIn("--onefile", text)
        self.assertIn("--windowed", text)
        self.assertIn("dist/Jarvis.exe", text)
        self.assertNotIn("Jarvis-Windows.zip", text)
        self.assertNotIn("Jarvis-Source-Bundle.zip", text)

    def test_component_fetcher_pins_the_four_original_fullstack_repositories(self):
        text = (ROOT / "scripts/fetch-fullstack-components.py").read_text(encoding="utf-8")
        for repo in (
            "jaredrhod/backtalk",
            "jaredrhod/ai-visualizer",
            "jaredrhod/barehands",
            "jaredrhod/ai-memory-vault",
        ):
            self.assertIn(repo, text)


if __name__ == "__main__":
    unittest.main()
