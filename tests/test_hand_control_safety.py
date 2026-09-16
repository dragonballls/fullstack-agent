import unittest

from quality_of_life.hand_control import HandControlBridge, HandEvent, HandGestureInterpreter, HandSample


class FakePyAutoGUI:
    def __init__(self):
        self.moves = []
        self.clicks = []
        self.mouse_up_count = 0

    def size(self):
        return (1920, 1080)

    def mouseUp(self, button="left"):
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


class HandControlSafetyTests(unittest.TestCase):
    def test_closed_fist_is_an_emergency_stop(self):
        interpreter = HandGestureInterpreter(pose_debounce_frames=1)
        bridge = HandControlBridge(enabled=True, controller=FakeController())
        events = interpreter.interpret(HandSample(0.5, 0.5, False, 0, 0.99), timestamp=0.0)
        self.assertEqual(events, (HandEvent(kind="pause"),))
        self.assertTrue(bridge.dispatch(events[0]))
        self.assertFalse(bridge.enabled)

    def test_bridge_maps_normalized_move_to_full_screen(self):
        controller = FakeController()
        bridge = HandControlBridge(enabled=True, controller=controller)
        self.assertTrue(bridge.dispatch(HandEvent(kind="move", x=0.5, y=0.5)))
        self.assertEqual(controller.moves, [(960, 540)])

    def test_disabled_bridge_never_dispatches_input(self):
        controller = FakeController()
        bridge = HandControlBridge(enabled=False, controller=controller)
        self.assertFalse(bridge.dispatch(HandEvent(kind="click")))
        self.assertEqual(controller.clicks, [])


if __name__ == "__main__":
    unittest.main()
