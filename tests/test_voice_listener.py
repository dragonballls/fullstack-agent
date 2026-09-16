import unittest
from unittest.mock import patch

from quality_of_life.voice_listener import LocalWakeWordListener, WakeEvent, VoiceListenerUnavailable


class VoiceListenerTests(unittest.TestCase):
    def test_repeated_wake_predictions_are_debounced(self):
        events = []
        listener = LocalWakeWordListener(on_wake=events.append, cooldown_seconds=10)
        with patch("quality_of_life.voice_listener.time.monotonic", side_effect=[100.0, 101.0, 111.0]):
            listener._emit_wake(0.8)
            listener._emit_wake(0.9)
            listener._emit_wake(0.95)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0], WakeEvent("hey_jarvis", 0.8))
        self.assertEqual(events[1], WakeEvent("hey_jarvis", 0.95))

    def test_missing_microphone_dependency_fails_closed(self):
        listener = LocalWakeWordListener()
        with patch("quality_of_life.voice_listener.importlib.import_module", side_effect=ImportError):
            with self.assertRaises(VoiceListenerUnavailable):
                listener._load_dependencies()

    def test_prediction_below_threshold_does_not_emit(self):
        events = []
        listener = LocalWakeWordListener(on_wake=events.append, threshold=0.70)
        listener.process_prediction({"hey_jarvis": 0.69})
        self.assertEqual(events, [])

    def test_prediction_at_threshold_emits(self):
        events = []
        listener = LocalWakeWordListener(on_wake=events.append, threshold=0.70)
        listener.process_prediction({"hey_jarvis": 0.70})
        self.assertEqual(events[0].model, "hey_jarvis")


if __name__ == "__main__":
    unittest.main()
