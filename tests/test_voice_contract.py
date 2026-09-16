from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VoiceContractTests(unittest.TestCase):
    def test_voice_contract_exists_and_is_secret_safe(self):
        contract = (ROOT / "JARVIS_VOICE.md").read_text(encoding="utf-8")
        self.assertIn("ElevenLabs", contract)
        self.assertIn("ELEVENLABS_API_KEY", contract)
        self.assertRegex(contract, r"(?i)(never|do not) (store|save).{0,50}API key")
        self.assertIn("real speech test", contract)
        self.assertIn("OmniRoute only", contract)
        self.assertIn("JARVIS_ALLOW_CLAUDE=false", contract)

    def test_jarvis_setup_is_claude_free(self):
        setup = (ROOT / "JARVIS_SETUP.md").read_text(encoding="utf-8")
        self.assertIn("OmniRoute only", setup)
        self.assertIn("Claude Code and a Claude subscription are not required", setup)
        self.assertIn("JARVIS_ALLOW_CLAUDE", setup)

    def test_installer_requires_voice_contract(self):
        installer = (ROOT / "JARVIS_SETUP.md").read_text(encoding="utf-8")
        self.assertIn("JARVIS_VOICE", installer)
        self.assertIn("OmniRoute", installer)

    def test_readme_discloses_cloud_voice_choice(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("ElevenLabs", readme)
        self.assertIn("Kokoro", readme)
        self.assertIn("OmniRoute only", readme)
        self.assertIn("Claude Code and a Claude subscription are not required", readme)
        self.assertIn("Jarvis profile is the primary product contract for this fork", readme)
        self.assertNotIn("Runs on: Claude Code only", readme)


if __name__ == "__main__":
    unittest.main()
