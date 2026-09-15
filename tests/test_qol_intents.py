import unittest

from quality_of_life.intents import parse_intent


class QoLIntentTests(unittest.TestCase):
    def test_location_intents(self):
        self.assertEqual(parse_intent("open Tokyo").kind, "place_search")
        self.assertEqual(parse_intent("show me Los Angeles").arguments["query"], "Los Angeles")
        self.assertEqual(parse_intent("where am I").kind, "locate_me")
        self.assertEqual(parse_intent("take me to the airport").kind, "route")

    def test_computer_and_chat_intents(self):
        move = parse_intent("move mouse to 100 200")
        self.assertEqual(move.kind, "computer_action")
        self.assertEqual(move.arguments, {"operation": "move", "x": 100, "y": 200})
        self.assertEqual(parse_intent("hello Jarvis").kind, "chat")
