from quality_of_life.intents import parse_intent


def test_location_intents():
    assert parse_intent("open Tokyo").kind == "place_search"
    assert parse_intent("show me Los Angeles").arguments["query"] == "Los Angeles"
    assert parse_intent("where am I").kind == "locate_me"
    assert parse_intent("take me to the airport").kind == "route"


def test_computer_and_chat_intents():
    move = parse_intent("move mouse to 100 200")
    assert move.kind == "computer_action"
    assert move.arguments == {"operation": "move", "x": 100, "y": 200}
    assert parse_intent("hello Jarvis").kind == "chat"
