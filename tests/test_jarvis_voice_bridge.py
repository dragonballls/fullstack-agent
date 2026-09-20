import os
import tempfile
import threading
import time
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from scripts.jarvis_voice_bridge import DEFAULT_CONFIG, JarvisVoiceBridge, _migrate_legacy_stt_default


class JarvisVoiceBridgeTests(TestCase):
    def test_default_voice_mode_is_live_and_cpu_stt(self):
        self.assertEqual(DEFAULT_CONFIG["mic_mode"], "open")
        self.assertEqual(DEFAULT_CONFIG["stt_device"], "cpu")
        self.assertEqual(DEFAULT_CONFIG["stt_compute"], "int8")

    def test_live_mode_aliases_normalize_to_live(self):
        bridge = JarvisVoiceBridge(controller=Mock(), ears=Mock(), mouth=Mock())
        with patch.dict(os.environ, {"JARVIS_MIC_MODE": "hands-free"}, clear=False):
            self.assertEqual(bridge._mode(), "live")

    def test_legacy_auto_and_float16_settings_migrate_to_cpu_int8(self):
        with tempfile.TemporaryDirectory() as temp:
            config_path = Path(temp) / "backtalk.json"
            config_path.write_text('{"stt_device": "auto", "stt_compute": "float16"}\n', encoding="utf-8")
            with patch("scripts.jarvis_voice_bridge.BACKTALK_CONFIG", config_path), patch.dict(
                os.environ, {"JARVIS_STT_DEVICE": ""}, clear=False
            ):
                migrated = _migrate_legacy_stt_default(
                    {"stt_device": "auto", "stt_compute": "float16", "voice": "bm_lewis"}
                )
            self.assertEqual(migrated["stt_device"], "cpu")
            self.assertEqual(migrated["stt_compute"], "int8")
            saved = config_path.read_text(encoding="utf-8")
            self.assertIn('"stt_device": "cpu"', saved)
            self.assertIn('"stt_compute": "int8"', saved)

    def test_explicit_stt_device_override_is_respected(self):
        config = {"stt_device": "cuda", "stt_compute": "float16"}
        with patch.dict(os.environ, {"JARVIS_STT_DEVICE": "cuda"}, clear=False):
            self.assertEqual(_migrate_legacy_stt_default(config), config)

    def test_transcript_uses_existing_jarvis_controller(self):
        controller = Mock()
        controller.execute_request.return_value = Mock(needs_confirmation=False, text="done")
        mouth = Mock()
        bridge = JarvisVoiceBridge(controller=controller, ears=Mock(), mouth=mouth, ptt=Mock())
        result = bridge.handle_transcript("open calculator")
        controller.execute_request.assert_called_once_with("open calculator", confirmed=False)
        mouth.say.assert_called_once_with("done")
        self.assertIsNotNone(result)


    def test_output_callback_receives_spoken_text(self):
        controller = Mock()
        controller.execute_request.return_value = Mock(needs_confirmation=False, text="done")
        mouth = Mock()
        transcript = []
        bridge = JarvisVoiceBridge(
            controller=controller,
            ears=Mock(),
            mouth=mouth,
            ptt=Mock(),
            on_output=transcript.append,
        )

        bridge.handle_transcript("hello")

        self.assertEqual(transcript, ["done"])
        mouth.say.assert_called_once_with("done")

    def test_identical_output_is_not_spoken_twice_immediately(self):
        callback = Mock()
        mouth = Mock()
        bridge = JarvisVoiceBridge(
            controller=Mock(),
            ears=Mock(),
            mouth=mouth,
            ptt=Mock(),
            on_output=callback,
        )

        bridge._speak("same response")
        bridge._speak("same response")

        callback.assert_called_once_with("same response")
        mouth.say.assert_called_once_with("same response")

    def test_voice_output_failure_does_not_escape_speech_boundary(self):
        controller = Mock()
        mouth = Mock()
        mouth.say.side_effect = RuntimeError("audio device disappeared")
        bridge = JarvisVoiceBridge(controller=controller, ears=Mock(), mouth=mouth, ptt=Mock())

        bridge._speak("hello")

        mouth.say.assert_called_once_with("hello")

    def test_confirmation_requires_a_second_confirmed_execution(self):
        controller = Mock()
        controller.execute_request.side_effect = [
            Mock(needs_confirmation=True, text="Confirm this action"),
            Mock(needs_confirmation=False, text="completed"),
        ]
        mouth = Mock()
        bridge = JarvisVoiceBridge(
            controller=controller,
            ears=Mock(),
            mouth=mouth,
            ptt=Mock(),
            confirmation=lambda _text: True,
        )
        bridge.handle_transcript("delete the file")
        self.assertEqual(controller.execute_request.call_args_list[0].kwargs, {"confirmed": False})
        self.assertEqual(controller.execute_request.call_args_list[1].kwargs, {"confirmed": True})
        self.assertEqual(mouth.say.call_count, 2)

    def test_live_listener_uses_speaker_gate_and_abort_signal(self):
        bridge = JarvisVoiceBridge(controller=Mock(), ears=Mock(), mouth=Mock())
        bridge.mouth.speaking = True
        calls = []

        def listen_once(**kwargs):
            calls.append(kwargs)
            bridge.stop_event.set()
            return None

        bridge.ears.listen_once.side_effect = listen_once
        bridge._run_live()

        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0]["gate"]())
        self.assertTrue(calls[0]["abort"]())

        bridge.mouth.speaking = False
        self.assertFalse(calls[0]["gate"]())

    def test_live_barge_in_cancels_speech_and_reuses_existing_controller(self):
        controller = Mock()
        controller.execute_request.return_value = Mock(needs_confirmation=False, text="done")
        mouth = Mock()
        ptt = Mock()
        record = Mock(return_value="hello")
        bridge = JarvisVoiceBridge(
            controller=controller,
            ears=Mock(),
            mouth=mouth,
            ptt=ptt,
            record_held=record,
        )
        bridge._barge_event.set()
        bridge._handle_live_barge()

        record.assert_called_once_with(ptt.is_held)
        controller.execute_request.assert_called_once_with("hello", confirmed=False)
        mouth.say.assert_called_once_with("done")

    def test_browser_playback_state_keeps_speaker_gate_closed(self):
        bridge = JarvisVoiceBridge(controller=Mock(), ears=Mock(), mouth=Mock())
        bridge.mouth.speaking = False

        self.assertFalse(bridge._speaker_gate())
        bridge.set_output_active(True)
        self.assertTrue(bridge._speaker_gate())
        bridge.set_output_active(False)
        self.assertFalse(bridge._speaker_gate())

    def test_stop_clears_browser_playback_state(self):
        bridge = JarvisVoiceBridge(controller=Mock(), ears=Mock(), mouth=Mock())
        bridge.set_output_active(True)
        bridge.stop()
        self.assertFalse(bridge._browser_audio_active)

    def test_stop_closes_audio_output_when_vendor_exposes_drop_out(self):
        controller = Mock()
        ears = Mock()
        mouth = Mock()
        mouth._drop_out = Mock()
        bridge = JarvisVoiceBridge(controller=controller, ears=ears, mouth=mouth, ptt=Mock())

        bridge.stop()

        mouth.shut_up.assert_called_once_with()
        mouth.shutdown.assert_called_once_with()
        mouth._drop_out.assert_called_once_with()

    def test_start_is_idempotent_with_injected_components(self):
        controller = Mock()
        ears = Mock()
        mouth = Mock()
        ptt = Mock()
        stopped = threading.Event()

        def fake_record(_is_held) -> str:
            stopped.wait()
            return ""

        bridge = JarvisVoiceBridge(
            controller=controller,
            ears=ears,
            mouth=mouth,
            ptt=ptt,
            record_held=fake_record,
        )
        ptt.wait_press.side_effect = lambda: None
        old_mode = os.environ.get("JARVIS_MIC_MODE")
        os.environ["JARVIS_MIC_MODE"] = "ptt"
        try:
            bridge.start()
            bridge.start()
            time.sleep(0.05)
            self.assertIsNotNone(bridge.thread)
            self.assertTrue(bridge.thread.is_alive())
        finally:
            stopped.set()
            bridge.stop()
            if old_mode is None:
                os.environ.pop("JARVIS_MIC_MODE", None)
            else:
                os.environ["JARVIS_MIC_MODE"] = old_mode


if __name__ == "__main__":
    import unittest
    unittest.main()
