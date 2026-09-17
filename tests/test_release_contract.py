from pathlib import Path
import unittest


class ReleaseContractTests(unittest.TestCase):
    def test_jarvis_release_gate_contains_all_required_release_stages(self):
        workflow = Path(".github/workflows/jarvis-release-gate.yml").read_text(encoding="utf-8")

        required = (
            "matrix.os",
            "matrix.python",
            "python -m compileall quality_of_life self_coding windows_maintenance scripts tests readiness.py",
            "python -m unittest discover -s tests -p 'test_*.py' -v",
            "Build single-file Jarvis.exe",
            "Smoke-test embedded visualizer",
            "Smoke-test the packaged native Jarvis host",
            "actions/attest@v4",
            "gh attestation verify dist/Jarvis.exe",
            "needs: windows-exe",
        )
        for token in required:
            self.assertIn(token, workflow, token)

    def test_windows_build_is_windowed_and_embeds_existing_fullstack_components(self):
        workflow = Path(".github/workflows/jarvis-release-gate.yml").read_text(encoding="utf-8")

        self.assertIn("'--onefile', '--windowed'", workflow)
        self.assertIn("build_vendor\\backtalk\\source", workflow)
        self.assertIn("build_vendor\\ai-visualizer\\source", workflow)
        self.assertIn("scripts/jarvis_desktop.pyw", workflow)

    def test_attestation_verification_precedes_release_publication(self):
        workflow = Path(".github/workflows/jarvis-release-gate.yml").read_text(encoding="utf-8")

        verify = workflow.index("gh attestation verify dist/Jarvis.exe")
        publish = workflow.index("softprops/action-gh-release@v2")
        self.assertLess(verify, publish)


if __name__ == "__main__":
    unittest.main()
