from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VoiceContractTests(unittest.TestCase):
    def test_voice_contract_exists_and_is_secret_safe(self):
        contract = (ROOT / "JARVIS_VOICE.md").read_text(encoding="utf-8")
        for phrase in ("ElevenLabs", "ELEVENLABS_API_KEY", "Never print the API key", "actual speech test"):
            self.assertIn(phrase, contract)

    def test_voice_contract_is_always_listening_and_omniroute_only(self):
        contract = (ROOT / "JARVIS_VOICE.md").read_text(encoding="utf-8").lower()
        for phrase in ("always listening", "wake word", "jarvis", "omniroute", "local-only", "one active voice session"):
            self.assertIn(phrase, contract)
        self.assertIn("jarvis_allow_claude=false", contract)

    def test_installer_requires_voice_contract(self):
        installer = (ROOT / "fullstack-agent.md").read_text(encoding="utf-8")
        self.assertIn("JARVIS_VOICE.md", installer)
        self.assertIn("OmniRoute", installer)

    def test_readme_discloses_cloud_voice_output(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("ElevenLabs", readme)
        self.assertIn("Kokoro", readme)
        self.assertIn("OmniRoute", readme)


if __name__ == "__main__":
    unittest.main()
