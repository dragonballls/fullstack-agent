from quality_of_life.hand_control import HandGestureInterpreter, HandSample


def test_pinch_emits_single_left_click_after_release():
    interpreter = HandGestureInterpreter()
    interpreter.interpret(HandSample(x=0.5, y=0.5, pinch=True, fingers=2, confidence=0.99), timestamp=0.0)
    events = interpreter.interpret(HandSample(x=0.5, y=0.5, pinch=False, fingers=1, confidence=0.99), timestamp=0.15)
    assert [event.kind for event in events] == ["click"]


def test_low_confidence_emits_nothing():
    interpreter = HandGestureInterpreter()
    events = interpreter.interpret(HandSample(x=0.5, y=0.5, pinch=True, fingers=2, confidence=0.2), timestamp=0.0)
    assert events == ()
