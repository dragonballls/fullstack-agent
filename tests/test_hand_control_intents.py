from quality_of_life.intents import parse_intent


def test_enable_hand_control_intent():
    assert parse_intent("turn on hand control").kind == "hand_control_start"
    assert parse_intent("enable webcam hand control").kind == "hand_control_start"


def test_stop_hand_control_intent():
    assert parse_intent("stop hand control").kind == "hand_control_stop"
    assert parse_intent("disable webcam control").kind == "hand_control_stop"
