from __future__ import annotations

import queue
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from scripts.jarvis_runtime_resilience import (
    JarvisResilientVoiceBridge,
    JarvisResilientWebApi,
    TEXT_INPUT_RESILIENCE_SCRIPT,
    _patch_mouth_instance,
)


class _FakeMouth:
    def __init__(self) -> None:
        self._q: queue.Queue = queue.Queue()
        self._speaking = False
        self._drop_count = 0
        self.shutdown_called = False
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def _run(self) -> None:
        while True:
            self._q.get()

    def shut_up(self) -> None:
        pass

    def shutdown(self) -> None:
        self.shutdown_called = True

    def _drop_out(self) -> None:
        self._drop_count += 1


class JarvisRuntimeResilienceTests(unittest.TestCase):
    def test_text_submission_never_routes_through_voice(self):
        controller = Mock()
        controller.execute_request.return_value = SimpleNamespace(text="done", needs_confirmation=False)
        voice = SimpleNamespace(bridge=Mock())
        host = SimpleNamespace(controller=controller, voice=voice)

        result = JarvisResilientWebApi(host).submit_text(" hello world ")

        controller.execute_request.assert_called_once_with("hello world", confirmed=False)
        voice.bridge.handle_transcript.assert_not_called()
        self.assertEqual(result["text"], "done")
        self.assertTrue(result["ok"])

    def test_center_hover_script_creates_hover_zone_and_preserves_space_default(self):
        self.assertIn('id = "jarvis-hover-zone"', TEXT_INPUT_RESILIENCE_SCRIPT)
        self.assertIn("event.stopImmediatePropagation()", TEXT_INPUT_RESILIENCE_SCRIPT)
        self.assertIn("Do not preventDefault", TEXT_INPUT_RESILIENCE_SCRIPT)
        self.assertIn("document.activeElement === input", TEXT_INPUT_RESILIENCE_SCRIPT)

    def test_mouth_worker_gets_clean_shutdown_sentinel(self):
        mouth = _FakeMouth()
        _patch_mouth_instance(mouth)

        mouth.shutdown()

        self.assertTrue(mouth.shutdown_called)
        self.assertFalse(mouth._worker.is_alive())
        self.assertGreaterEqual(mouth._drop_count, 1)
        self.assertTrue(getattr(mouth, "_jarvis_shutdown_complete", False))

        # The lifecycle wrapper is idempotent.
        mouth.shutdown()
        self.assertGreaterEqual(mouth._drop_count, 1)

    def test_stt_preflight_failure_stays_in_voice_layer(self):
        bridge = JarvisResilientVoiceBridge(Mock(), ears=Mock(), mouth=Mock())
        with patch("scripts.jarvis_runtime_resilience.importlib.import_module", side_effect=RuntimeError("STT unavailable")):
            self.assertFalse(bridge._prepare_stt())
        self.assertTrue(bridge.stop_event.is_set())

    def test_stt_preflight_uses_real_backtalk_warm(self):
        bridge = JarvisResilientVoiceBridge(Mock(), ears=Mock(), mouth=Mock())
        module = SimpleNamespace(warm=Mock())
        with patch("scripts.jarvis_runtime_resilience.importlib.import_module", return_value=module):
            self.assertTrue(bridge._prepare_stt())
        module.warm.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
