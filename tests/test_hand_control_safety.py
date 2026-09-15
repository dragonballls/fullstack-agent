from quality_of_life.hand_control import HandControlBridge, HandEvent, HandGestureInterpreter, HandSample


class FakePyAutoGUI:
    def __init__(self):
        self.moves = []
        self.clicks = []
        self.mouse_up_count = 0

    def size(self):
        return (1920, 1080)

    def mouseUp(self):
        self.mouse_up_count += 1


class FakeController:
    def __init__(self):
        self.pyautogui = FakePyAutoGUI()
        self.moves = []
        self.clicks = []

    def move(self, x, y):
        self.moves.append((x, y))

    def click(self, button="left", clicks=1):
        self.clicks.append((button, clicks))


def test_closed_fist_is_an_emergency_stop():
    interpreter = HandGestureInterpreter()
    bridge = HandControlBridge(enabled=True, controller=FakeController())
    events = interpreter.interpret(HandSample(0.5, 0.5, False, 0, 0.99), timestamp=0.0)
    assert events == (HandEvent(kind="pause"),)
    assert bridge.dispatch(events[0]) is True
    assert bridge.enabled is False


def test_bridge_maps_normalized_move_to_full_screen():
    controller = FakeController()
    bridge = HandControlBridge(enabled=True, controller=controller)
    assert bridge.dispatch(HandEvent(kind="move", x=0.5, y=0.5)) is True
    assert controller.moves == [(960, 540)]


def test_disabled_bridge_never_dispatches_input():
    controller = FakeController()
    bridge = HandControlBridge(enabled=False, controller=controller)
    assert bridge.dispatch(HandEvent(kind="click")) is False
    assert controller.clicks == []
