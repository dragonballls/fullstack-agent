import os
import threading
import time
from unittest import TestCase
from unittest.mock import Mock

from scripts.jarvis_voice_bridge import DEFAULT_CONFIG, JarvisVoiceBridge


class JarvisVoiceBridgeTests(TestCase):
    def test_default_stt_device_avoids_gpu_auto_detection(self):
        self.assertEqual(DEFAULT_CONFIG["stt_device"], "cpu")

    def test_transcript_uses_existing_jarvis_controller(self):
        controller = Mock()
        controller.execute_request.return_value = Mock(needs_confirmation=False, text="done")
        mouth = Mock()
        bridge = JarvisVoiceBridge(controller=controller, ears=Mock(), mouth=mouth, ptt=Mock())
        result = bridge.handle_transcript("open calculator")
        controller.execute_request.assert_called_once_with("open calculator", confirmed=False)
        mouth.say.assert_called_once_with("done")
        self.assertIsNotNone(result)

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
