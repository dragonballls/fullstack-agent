from quality_of_life.hand_control import HandGestureInterpreter, HandSample


def test_pointing_emits_cursor_move():
    interpreter = HandGestureInterpreter()
    events = interpreter.interpret(HandSample(x=0.25, y=0.40, pinch=False, fingers=1, confidence=0.99), timestamp=0.0)
    assert events == (events[0],)
    assert events[0].kind == "move"
    assert events[0].x == 0.25
    assert events[0].y == 0.40


def test_pinch_release_emits_one_click():
    interpreter = HandGestureInterpreter()
    interpreter.interpret(HandSample(x=0.5, y=0.5, pinch=True, fingers=2, confidence=0.99), timestamp=0.0)
    events = interpreter.interpret(HandSample(x=0.5, y=0.5, pinch=False, fingers=1, confidence=0.99), timestamp=0.15)
    assert [event.kind for event in events] == ["click"]


def test_low_confidence_is_rejected():
    interpreter = HandGestureInterpreter()
    events = interpreter.interpret(HandSample(x=0.5, y=0.5, pinch=True, fingers=2, confidence=0.20), timestamp=0.0)
    assert events == ()
