from unittest import TestCase
from unittest.mock import Mock

from scripts.jarvis_desktop import FullstackJarvisHost


class FullstackJarvisHostTests(TestCase):
    def test_start_initializes_fullstack_components_once(self):
        controller = Mock()
        visualizer = Mock()
        voice = Mock()
        hands = Mock()
        host = FullstackJarvisHost(controller, visualizer=visualizer, voice=voice, hands=hands)
        host.start()
        host.start()
        visualizer.start.assert_called_once()
        voice.start.assert_called_once()
        hands.start.assert_called_once()
        self.assertTrue(host.started)

    def test_stop_is_idempotent(self):
        controller = Mock()
        visualizer = Mock()
        voice = Mock()
        hands = Mock()
        host = FullstackJarvisHost(controller, visualizer=visualizer, voice=voice, hands=hands)
        host.start()
        host.stop()
        host.stop()
        visualizer.stop.assert_called_once()
        voice.stop.assert_called_once()
        hands.stop.assert_called_once()
        controller.close.assert_called_once()
        self.assertTrue(host.stopped)


if __name__ == "__main__":
    import unittest
    unittest.main()
