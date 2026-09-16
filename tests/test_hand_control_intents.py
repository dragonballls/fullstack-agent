import unittest

from quality_of_life.intents import parse_intent


class HandControlIntentTests(unittest.TestCase):
    def test_enable_hand_control_intent(self):
        self.assertEqual(parse_intent("turn on hand control").kind, "hand_control_start")
        self.assertEqual(parse_intent("enable webcam hand control").kind, "hand_control_start")

    def test_stop_hand_control_intent(self):
        self.assertEqual(parse_intent("stop hand control").kind, "hand_control_stop")
        self.assertEqual(parse_intent("disable webcam control").kind, "hand_control_stop")


if __name__ == "__main__":
    unittest.main()
