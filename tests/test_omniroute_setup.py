import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quality_of_life.omniroute_setup import OmniRouteProvisioner


class OmniRouteSetupTests(unittest.TestCase):
    def test_default_data_dir_is_user_local(self):
        with TemporaryDirectory() as tmp:
            provisioner = OmniRouteProvisioner(data_dir=Path(tmp) / "OmniRoute")
            self.assertEqual(provisioner.data_dir, Path(tmp) / "OmniRoute")

    def test_configure_provider_sends_secret_only_on_stdin(self):
        with TemporaryDirectory() as tmp:
            provisioner = OmniRouteProvisioner(data_dir=Path(tmp))
            provisioner._resolved = ("omniroute",)
            provisioner._source = "test"

            class Completed:
                returncode = 0
                stdout = ""
                stderr = ""

            with patch("quality_of_life.omniroute_setup.subprocess.run", return_value=Completed()) as run:
                result = provisioner.configure_provider("openai", "test-secret-123456")
            self.assertTrue(result["ok"])
            args = run.call_args
            self.assertIn("--credential-stdin", args.args[0])
            self.assertNotIn("test-secret-123456", args.args[0])
            self.assertEqual(args.kwargs["input"], "test-secret-123456\n")

    def test_provider_listing_never_returns_credentials(self):
        with TemporaryDirectory() as tmp:
            provisioner = OmniRouteProvisioner(data_dir=Path(tmp))
            provisioner._resolved = ("omniroute",)
            provisioner._source = "test"
            secret = "test-secret-123456"

            class Completed:
                returncode = 0
                stdout = json.dumps({"connections": [{"name": "openai", "status": "configured", "credential": secret}]})
                stderr = ""

            with patch("quality_of_life.omniroute_setup.subprocess.run", return_value=Completed()):
                providers = provisioner.list_providers()
            self.assertEqual(providers, [{"name": "openai", "status": "configured"}])
            self.assertNotIn(secret, json.dumps(providers))

    def test_provider_name_is_normalized_and_invalid_names_rejected(self):
        with TemporaryDirectory() as tmp:
            provisioner = OmniRouteProvisioner(data_dir=Path(tmp))
            provisioner._resolved = ("omniroute",)

            class Completed:
                returncode = 0
                stdout = ""
                stderr = ""

            with patch("quality_of_life.omniroute_setup.subprocess.run", return_value=Completed()) as run:
                result = provisioner.configure_provider(" OpenAI ", "valid-key-123")
            self.assertEqual(result["provider"], "openai")
            self.assertIn("providers", run.call_args.args[0])
            with self.assertRaises(ValueError):
                provisioner.configure_provider("bad provider", "valid-key-123")

    def test_embedded_runtime_is_preferred_when_available(self):
        with TemporaryDirectory() as tmp:
            provisioner = OmniRouteProvisioner(data_dir=Path(tmp))
            with patch.object(provisioner, "_packaged_command", return_value=("node.exe", "omniroute.mjs")):
                command = provisioner.resolve_command(install_if_missing=False)
            self.assertEqual(command, ("node.exe", "omniroute.mjs"))
            self.assertEqual(provisioner._source, "bundled")


if __name__ == "__main__":
    unittest.main()
