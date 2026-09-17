from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from quality_of_life.omniroute_lifecycle import OmniRouteLifecycle


class OmniRouteLifecycleTests(unittest.TestCase):
    def test_default_command_is_headless(self):
        lifecycle = OmniRouteLifecycle("http://127.0.0.1:20128/v1")
        self.assertEqual(lifecycle.command, "omniroute --no-open")

    def test_loopback_startup_launches_once_then_waits_for_health(self):
        lifecycle = OmniRouteLifecycle(
            "http://127.0.0.1:20128/v1",
            startup_timeout=1,
            poll_interval=0.01,
        )
        process = Mock()
        process.poll.return_value = None
        with patch.object(lifecycle, "_probe", side_effect=(False, True)) as probe, patch.object(
            lifecycle, "_command_argv", return_value=["omniroute", "--no-open"]
        ) as argv, patch("subprocess.Popen", return_value=process) as popen:
            self.assertTrue(lifecycle.ensure_available())
        probe.assert_called()
        argv.assert_called_once_with()
        popen.assert_called_once()
        self.assertEqual(popen.call_args.args[0], ["omniroute", "--no-open"])

    def test_remote_target_never_gets_started_by_local_lifecycle(self):
        lifecycle = OmniRouteLifecycle("https://gateway.example/v1")
        with patch.object(lifecycle, "_probe", return_value=False), patch("subprocess.Popen") as popen:
            self.assertTrue(lifecycle.ensure_available())
        popen.assert_not_called()

    def test_missing_command_fails_with_actionable_message(self):
        lifecycle = OmniRouteLifecycle("http://127.0.0.1:20128/v1", command="missing-omniroute")
        with patch.object(lifecycle, "_probe", return_value=False), patch("shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "command was not found"):
                lifecycle.ensure_available()


if __name__ == "__main__":
    unittest.main()
