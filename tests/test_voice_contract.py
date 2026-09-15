from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VoiceContractTests(unittest.TestCase):
    def test_voice_contract_exists_and_is_secret_safe(self):
        contract = (ROOT / "JARVIS_VOICE.md").read_text(encoding="utf-8")
        self.assertIn("ElevenLabs", contract)
        self.assertIn("ELEVENLABS_API_KEY", contract)
        self.assertIn("Never print the API key", contract)
        self.assertIn("real speech test", contract)

    def test_installer_requires_voice_contract(self):
        installer = (ROOT / "fullstack-agent.md").read_text(encoding="utf-8")
        self.assertIn("JARVIS_VOICE.md", installer)
        self.assertIn("actual speech test", installer)

    def test_readme_discloses_cloud_voice_choice(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("ElevenLabs", readme)
        self.assertIn("Kokoro", readme)


if __name__ == "__main__":
    unittest.main()
