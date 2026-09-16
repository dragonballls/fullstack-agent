import os
import threading
import time
from unittest import TestCase
from unittest.mock import Mock

from scripts.jarvis_voice_bridge import JarvisVoiceBridge


class JarvisVoiceBridgeTests(TestCase):
    def test_transcript_uses_existing_jarvis_controller(self):
        controller = Mock()
        controller.execute_request.return_value = Mock(needs_confirmation=False, text="done")
        mouth = Mock()
        bridge = JarvisVoiceBridge(controller=controller, ears=Mock(), mouth=mouth, ptt=Mock())
        result = bridge.handle_transcript("open calculator")
        controller.execute_request.assert_called_once_with("open calculator", confirmed=False)
        mouth.say.assert_called_once_with("done")
        self.assertIsNotNone(result)

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

    def test_start_is_idempotent_with_injected_components(self):
        controller = Mock()
        ears = Mock()
        mouth = Mock()
        ptt = Mock()
        bridge = JarvisVoiceBridge(controller=controller, ears=ears, mouth=mouth, ptt=ptt)
        stopped = threading.Event()

        def wait_press() -> None:
            while not stopped.wait(0.02):
                pass

        ptt.wait_press.side_effect = wait_press
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
