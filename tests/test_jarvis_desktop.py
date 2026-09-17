from __future__ import annotations

from types import ModuleType, SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

from scripts import jarvis_desktop
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

    def test_native_window_uses_resizable_default_and_windows_edgechromium(self):
        controller = Mock()
        visualizer = Mock()
        visualizer.url.return_value = "http://127.0.0.1:8790/faces/board/"
        host = FullstackJarvisHost(controller, visualizer=visualizer, voice=Mock(), hands=Mock())

        fake_webview = ModuleType("webview")
        fake_webview.create_window = Mock(return_value=SimpleNamespace())
        fake_webview.start = Mock()

        with patch.object(sys, "platform", "win32"), patch.dict(sys.modules, {"webview": fake_webview}):
            host.run_window()

        fake_webview.create_window.assert_called_once_with(
            title="Jarvis",
            url="http://127.0.0.1:8790/faces/board/",
            width=1200,
            height=800,
            fullscreen=False,
            resizable=True,
            min_size=(800, 600),
            js_api=host.web_api,
        )
        fake_webview.start.assert_called_once_with(gui="edgechromium", debug=False)
        self.assertIsNotNone(host._window)

    def test_text_input_api_is_exposed_to_native_window(self):
        self.assertTrue(hasattr(jarvis_desktop, "JarvisWebApi"))
        self.assertTrue(hasattr(jarvis_desktop, "TEXT_INPUT_SCRIPT"))
        self.assertIn("pywebview.api.submit_text", jarvis_desktop.TEXT_INPUT_SCRIPT)
        self.assertIn("mouseenter", jarvis_desktop.TEXT_INPUT_SCRIPT)
        self.assertIn("keydown", jarvis_desktop.TEXT_INPUT_SCRIPT)

    def test_text_input_api_routes_to_jarvis_voice_bridge(self):
        controller = Mock()
        controller.runtime = Mock()
        voice = SimpleNamespace(bridge=Mock())
        voice.bridge.handle_transcript.return_value = SimpleNamespace(needs_confirmation=False, text="done")
        host = FullstackJarvisHost(controller, voice=voice)
        api = host.web_api

        result = api.submit_text("  hello Jarvis  ")

        voice.bridge.handle_transcript.assert_called_once_with("hello Jarvis")
        self.assertEqual(result["ok"], True)
        self.assertEqual(result["text"], "done")
        self.assertFalse(result["needs_confirmation"])

    def test_text_input_api_falls_back_to_controller_when_voice_unavailable(self):
        controller = Mock()
        controller.runtime = Mock()
        controller.execute_request.return_value = SimpleNamespace(
            needs_confirmation=False,
            text="controller response",
        )
        host = FullstackJarvisHost(controller, voice=SimpleNamespace(bridge=None))

        result = host.web_api.submit_text(" run diagnostics ")

        controller.execute_request.assert_called_once_with("run diagnostics", confirmed=False)
        self.assertEqual(result["text"], "controller response")
        self.assertFalse(result["needs_confirmation"])

    def test_frozen_backtalk_smoke_mode_validates_embedded_modules_without_audio_hardware(self):
        controller = Mock()
        adapter = VoiceAdapter(controller)
        fake_vendor = "/tmp/embedded-backtalk"

        root = ModuleType("backtalk")
        ears = ModuleType("backtalk.ears")
        mouth = ModuleType("backtalk.mouth")
        ptt = ModuleType("backtalk.ptt")

        class Ears:
            pass

        class Mouth:
            pass

        class PTTListener:
            pass

        ears.Ears = Ears
        mouth.Mouth = Mouth
        ptt.PTTListener = PTTListener

        with patch.dict("os.environ", {"JARVIS_SMOKE": "1", "JARVIS_SMOKE_VOICE": "1"}), patch(
            "scripts.jarvis_desktop.embedded_path", return_value=fake_vendor
        ), patch.dict(
            sys.modules,
            {
                "backtalk": root,
                "backtalk.ears": ears,
                "backtalk.mouth": mouth,
                "backtalk.ptt": ptt,
            },
        ):
            adapter.start()

        self.assertIsNone(adapter.bridge)
