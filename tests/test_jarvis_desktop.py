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

        self.assertEqual(fake_webview.create_window.call_count, 2)
        self.assertEqual(
            fake_webview.create_window.call_args_list[0].kwargs,
            {
                "title": "Jarvis",
                "url": "http://127.0.0.1:8790/faces/board/",
                "width": 1200,
                "height": 800,
                "fullscreen": False,
                "resizable": True,
                "min_size": (800, 600),
                "js_api": host.web_api,
            },
        )
        floating_kwargs = fake_webview.create_window.call_args_list[1].kwargs
        self.assertEqual(floating_kwargs["title"], "Jarvis Floating Text Link")
        self.assertIn("html", floating_kwargs)
        self.assertIs(floating_kwargs["js_api"], host.web_api)
        self.assertTrue(floating_kwargs["hidden"])
        self.assertTrue(floating_kwargs["frameless"])
        self.assertTrue(floating_kwargs["easy_drag"])
        self.assertTrue(floating_kwargs["on_top"])
        fake_webview.start.assert_called_once_with(gui="edgechromium", debug=False)
        self.assertIsNotNone(host._window)

    def test_omniroute_provider_api_is_exposed(self):
        self.assertTrue(hasattr(jarvis_desktop, "OMNIROUTE_SETTINGS_HTML"))
        self.assertIn("open_omniroute_settings", dir(jarvis_desktop.JarvisWebApi))
        self.assertIn("omniroute_configure_provider", dir(jarvis_desktop.JarvisWebApi))
        self.assertIn('type="password"', jarvis_desktop.OMNIROUTE_SETTINGS_HTML)
        self.assertIn("CONNECT & TEST", jarvis_desktop.OMNIROUTE_SETTINGS_HTML)

    def test_omniroute_and_elevenlabs_shared_settings_surface(self):
        html = jarvis_desktop.OMNIROUTE_SETTINGS_HTML
        for token in (
            "Auto-detect from API key",
            "omniroute_detect_provider",
            "VOICE ENGINE · ELEVENLABS",
            "SAVE & TEST VOICE",
            "elevenlabs_configure",
            "elevenlabs_test",
            "elevenlabs_voices",
        ):
            self.assertIn(token, html)
        for method in (
            "voice_audio",
            "elevenlabs_status",
            "elevenlabs_configure",
            "elevenlabs_test",
            "elevenlabs_voices",
            "omniroute_detect_provider",
        ):
            self.assertIn(method, dir(jarvis_desktop.JarvisWebApi))

    def test_voice_adapter_uses_elevenlabs_as_mouth(self):
        controller = Mock()
        adapter = VoiceAdapter(controller)
        self.assertIsInstance(adapter.elevenlabs, jarvis_desktop.ElevenLabsMouth)

    def test_voice_audio_drains_elevenlabs_packets(self):
        controller = Mock()
        host = FullstackJarvisHost(controller, voice=SimpleNamespace(elevenlabs=Mock()), hands=Mock())
        host.voice.elevenlabs.take_audio.return_value = [{"sequence": 1, "mime": "audio/mpeg", "data": "YQ=="}]
        self.assertEqual(host.voice_audio()["items"][0]["sequence"], 1)
        host.voice.elevenlabs.take_audio.assert_called_once_with()

    def test_auto_detect_api_method_never_receives_provider_secret_back(self):
        controller = Mock()
        host = FullstackJarvisHost(controller, voice=Mock(), hands=Mock())
        result = host.web_api.omniroute_detect_provider("sk-ant-example")
        self.assertEqual(result, {"ok": True, "provider": "anthropic", "detected": True})
        self.assertNotIn("sk-ant-example", repr(result))

    def test_omniroute_status_uses_secret_free_summary(self):
        controller = Mock()
        controller.runtime = Mock()
        host = FullstackJarvisHost(controller, voice=Mock(), hands=Mock())
        host.omniroute = Mock()
        host.omniroute.status.return_value.as_dict.return_value = {
            "available": True,
            "source": "bundled",
            "version": "3.8.51",
            "base_url": "http://127.0.0.1:20128/v1",
            "data_dir": "/safe",
        }
        host.omniroute.ensure_running.return_value = True
        host.omniroute.list_providers.return_value = [{"name": "openai", "status": "connected"}]
        result = host.omniroute_status()
        self.assertEqual(result["version"], "3.8.51")
        self.assertEqual(result["providers"], [{"name": "openai", "status": "connected"}])
        self.assertNotIn("api_key", repr(result))

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

    def test_voice_adapter_can_be_stopped_without_live_provider(self):
        controller = Mock()
        adapter = VoiceAdapter(controller)
        adapter.stop()
        self.assertIsNone(adapter.bridge)

    def test_embedded_text_and_settings_javascript_parse_when_node_exists(self):
        node = __import__("shutil").which("node")
        if node is None:
            self.skipTest("node is not installed on this runner")
        import re
        import subprocess
        import tempfile
        cases = [
            (jarvis_desktop.TEXT_INPUT_SCRIPT, "text-input", False),
            (jarvis_desktop.OMNIROUTE_SETTINGS_HTML, "settings", True),
        ]
        for source, label, is_html in cases:
            scripts = (
                re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", source, re.DOTALL | re.IGNORECASE)
                if is_html else [source]
            )
            self.assertTrue(scripts, label)
            with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
                handle.write("\n".join(scripts))
                path = handle.name
            try:
                result = subprocess.run([node, "--check", path], capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            finally:
                __import__("os").unlink(path)

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
