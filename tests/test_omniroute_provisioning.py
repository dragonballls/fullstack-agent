from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quality_of_life.omniroute_setup import OmniRouteProvisioner, default_data_dir


class OmniRouteProvisionerTests(unittest.TestCase):
    def test_default_data_dir_is_jarvis_owned(self):
        path = default_data_dir()
        self.assertIn("Jarvis", str(path))
        self.assertTrue(str(path).lower().endswith("omniroute"))

    def test_bundled_command_is_preferred_when_present(self):
        provisioner = OmniRouteProvisioner()
        root = Path(tempfile.mkdtemp(prefix="jarvis-omni-test-"))
        try:
            (root / "node_modules" / "omniroute" / "bin").mkdir(parents=True)
            (root / "node.exe").write_bytes(b"node")
            (root / "node_modules" / "omniroute" / "bin" / "omniroute.mjs").write_text("console.log('ok')", encoding="utf-8")
            with patch("quality_of_life.omniroute_setup._packaged_runtime_root", return_value=root):
                command = provisioner._packaged_command()
            self.assertEqual(command, (str(root / "node.exe"), str(root / "node_modules" / "omniroute" / "bin" / "omniroute.mjs")))
        finally:
            import shutil
            shutil.rmtree(root, ignore_errors=True)

    def test_ensure_running_starts_headless_gateway_and_waits_for_probe(self):
        provisioner = OmniRouteProvisioner()
        process = unittest.mock.Mock()
        process.poll.return_value = None
        with patch.object(provisioner, "command_argv", return_value=["omniroute", "--no-open"]), patch.object(
            provisioner, "_probe", side_effect=(False, True)
        ), patch("subprocess.Popen", return_value=process) as popen:
            self.assertTrue(provisioner.ensure_running(wait_seconds=1))
        popen.assert_called_once()
        self.assertEqual(popen.call_args.args[0], ["omniroute", "--no-open", "--port", "20128"])

    def test_status_never_exposes_provider_credentials(self):
        provisioner = OmniRouteProvisioner()
        with patch.object(provisioner, "resolve_command", return_value=("omniroute",)), patch.object(
            provisioner, "_version", return_value="3.8.51"
        ):
            status = provisioner.status().as_dict()
        self.assertNotIn("api_key", status)
        self.assertNotIn("secret", repr(status))

    def test_provider_key_is_sent_only_over_stdin(self):
        provisioner = OmniRouteProvisioner(data_dir=Path(tempfile.mkdtemp(prefix="jarvis-omni-data-")))
        with patch.object(provisioner, "command_argv", return_value=["omniroute"]):
            with patch("subprocess.run") as run:
                run.return_value.returncode = 0
                result = provisioner.configure_provider("openai", "super-secret-provider-key")
        self.assertTrue(result["ok"])
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs["input"], "super-secret-provider-key\n")
        argv = run.call_args.args[0]
        self.assertNotIn("super-secret-provider-key", argv)
        self.assertNotIn("super-secret-provider-key", kwargs.get("env", {}).values())

    def test_provider_listing_is_redacted_to_name_and_status(self):
        provisioner = OmniRouteProvisioner()
        fake = '{"connections":[{"id":"1","name":"openai","status":"connected","apiKey":"SECRET"}]}'
        with patch.object(provisioner, "command_argv", return_value=["omniroute"]):
            with patch("subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = fake
                providers = provisioner.list_providers()
        self.assertEqual(providers, [{"name":"openai","status":"connected"}])
        self.assertNotIn("SECRET", repr(providers))

    def test_short_provider_key_is_rejected_before_process_launch(self):
        provisioner = OmniRouteProvisioner()
        with patch("subprocess.run") as run:
            with self.assertRaisesRegex(ValueError, "too short"):
                provisioner.configure_provider("openai", "short")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
