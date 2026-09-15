from quality_of_life.hand_control import HandGestureInterpreter, HandSample


def test_pointing_moves_cursor():
    interpreter = HandGestureInterpreter()
    events = interpreter.interpret(HandSample(x=0.25, y=0.4, pinch=False, fingers=1, confidence=0.99), timestamp=0.0)
    assert any(event.kind == "move" for event in events)
