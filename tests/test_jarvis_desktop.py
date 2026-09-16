from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts.jarvis_desktop import FullstackJarvisHost, JarvisDesktopController, VoiceAdapter, build_runtime


class JarvisDesktopTests(unittest.TestCase):
    def test_build_runtime_uses_guarded_runtime(self):
        runtime = build_runtime()
        self.assertIsNotNone(runtime.policy)
        self.assertIn("computer", runtime.available_tools())

    def test_execute_request_forwards_confirmation(self):
        runtime = Mock()
        runtime._assistant_orchestrator.return_value.execute.return_value = "result"
        controller = JarvisDesktopController(runtime=runtime)
        controller.execute_request("open calculator", confirmed=True)
        runtime._assistant_orchestrator.return_value.execute.assert_called_once_with(
            "open calculator", confirmed=True
        )
        controller.close()

    def test_empty_request_is_rejected_before_orchestrator(self):
        runtime = Mock()
        controller = JarvisDesktopController(runtime=runtime)
        with self.assertRaises(ValueError):
            controller.execute_request("   ")
        runtime._assistant_orchestrator.return_value.execute.assert_not_called()
        controller.close()

    def test_confirmation_result_does_not_auto_retry(self):
        controller = Mock()
        result = SimpleNamespace(needs_confirmation=True, text="confirm required")
        controller.execute_request.return_value = result
        observed = controller.execute_request("remove app", confirmed=False)
        self.assertTrue(observed.needs_confirmation)
        controller.execute_request.assert_called_once_with("remove app", confirmed=False)

    def test_voice_start_failure_does_not_take_down_visualizer(self):
        controller = Mock()
        controller.runtime = Mock()
        visualizer = Mock()
        voice = Mock()
        voice.start.side_effect = RuntimeError("Backtalk audio device unavailable")
        hands = Mock()
        host = FullstackJarvisHost(
            controller,
            visualizer=visualizer,
            voice=voice,
            hands=hands,
        )
        host.updater = Mock()

        host.start()

        self.assertTrue(host.started)
        visualizer.start.assert_called_once_with()
        visualizer.stop.assert_not_called()
        hands.start.assert_called_once_with()

        host.stop()
        visualizer.stop.assert_called_once_with()

    def test_frozen_backtalk_smoke_mode_validates_embedded_modules_without_audio_hardware(self):
        controller = Mock()
        adapter = VoiceAdapter(controller)
        fake_vendor = "/tmp/embedded-backtalk"
        with patch.dict("os.environ", {"JARVIS_SMOKE": "1", "JARVIS_SMOKE_VOICE": "1"}), patch(
            "scripts.jarvis_desktop.embedded_path", return_value=fake_vendor
        ), patch("builtins.__import__") as imported:
            # Smoke validation should import the three upstream contracts and stop
            # before constructing microphone/speaker objects.
            adapter.start()
            imported.assert_any_call("backtalk.ears", fromlist=["Ears"])
            imported.assert_any_call("backtalk.mouth", fromlist=["Mouth"])
            imported.assert_any_call("backtalk.ptt", fromlist=["PTTListener"])
