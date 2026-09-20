import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quality_of_life.omniroute_setup import OmniRouteProvisioner, detect_provider_from_key


class OmniRouteSetupTests(unittest.TestCase):
    def test_auto_detects_only_unambiguous_provider_key_formats(self):
        cases = {
            "sk-ant-example-123456": "anthropic",
            "sk-or-v1-example-123456": "openrouter",
            "gsk_example_123456": "groq",
            "xai-example-123456": "xai",
            "AIzaExample12345678": "gemini",
            "csk-example-123456": "cerebras",
            "sk-proj-example-123456": "openai",
            "sk-svcacct-example-123456": "openai",
        }
        for key, provider in cases.items():
            self.assertEqual(detect_provider_from_key(key), provider)
        self.assertIsNone(detect_provider_from_key("sk-generic-example-123456"))
        self.assertIsNone(detect_provider_from_key("unknown-format-123456"))

    def test_auto_provider_uses_detected_slot_without_exposing_secret(self):
        provisioner = OmniRouteProvisioner()
        provisioner._resolved = ("omniroute",)
        secret = "sk-ant-secret-123456"
        class Completed:
            returncode = 0
            stdout = ""
            stderr = ""
        with patch("quality_of_life.omniroute_setup.subprocess.run", return_value=Completed()) as run:
            result = provisioner.configure_provider("auto", secret)
        self.assertEqual(result["provider"], "anthropic")
        self.assertNotIn(secret, run.call_args.args[0])
        self.assertEqual(run.call_args.kwargs["input"], secret + "\n")

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

    def test_start_creates_missing_working_directory_before_popen(self):
        with TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "OmniRoute"
            provisioner = OmniRouteProvisioner(data_dir=data_dir)
            provisioner._resolved = ("node.exe", "omniroute.mjs")
            provisioner._source = "bundled"

            class Process:
                def poll(self):
                    return 0

            with patch.object(provisioner, "_probe", return_value=False):
                with patch(
                    "quality_of_life.omniroute_setup.subprocess.Popen",
                    return_value=Process(),
                ) as popen:
                    self.assertFalse(provisioner.ensure_running(wait_seconds=0.5))

            self.assertTrue(data_dir.is_dir())
            self.assertEqual(popen.call_args.kwargs["cwd"], str(data_dir))
            if provisioner._process_log_handle is not None:
                provisioner._process_log_handle.close()
                provisioner._process_log_handle = None


if __name__ == "__main__":
    unittest.main()
