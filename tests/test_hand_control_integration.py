import unittest

from quality_of_life.hand_control import HandControlBridge, HandGestureInterpreter, HandSample


class FakePyAutoGUI:
    def __init__(self):
        self.calls = []

    def size(self):
        return 1920, 1080

    def mouseDown(self, button="left"):
        self.calls.append(("down", button))

    def mouseUp(self, button="left"):
        self.calls.append(("up", button))


class FakeController:
    def __init__(self):
        self.pyautogui = FakePyAutoGUI()
        self.calls = []

    def move(self, x, y):
        self.calls.append(("move", x, y))

    def click(self, button="left", clicks=1):
        self.calls.append(("click", button, clicks))

    def scroll(self, amount):
        self.calls.append(("scroll", amount))


class HandControlIntegrationTests(unittest.TestCase):
    def test_interpreter_to_bridge_pipeline(self):
        controller = FakeController()
        bridge = HandControlBridge(enabled=True, controller=controller)
        interpreter = HandGestureInterpreter(move_deadzone=0.01, drag_hold_s=0.3, click_cooldown_s=0.0)

        samples = [
            HandSample(0.20, 0.30, False, 1, 0.99),
            HandSample(0.25, 0.35, False, 1, 0.99),
            HandSample(0.25, 0.35, True, 1, 0.99),
            HandSample(0.25, 0.35, True, 1, 0.99),
            HandSample(0.25, 0.35, False, 1, 0.99),
        ]
        for timestamp, sample in enumerate(samples):
            for event in interpreter.interpret(sample, timestamp=timestamp / 10):
                self.assertTrue(bridge.dispatch(event))

        self.assertIn(("move", 480, 324), controller.calls)
        self.assertIn(("down", "left"), controller.pyautogui.calls)
        self.assertIn(("up", "left"), controller.pyautogui.calls)

    def test_disabled_bridge_never_dispatches_input(self):
        controller = FakeController()
        bridge = HandControlBridge(enabled=False, controller=controller)
        interpreter = HandGestureInterpreter()
        for event in interpreter.interpret(HandSample(0.5, 0.5, False, 1, 0.99), timestamp=0.0):
            self.assertFalse(bridge.dispatch(event))
        self.assertEqual(controller.calls, [])


if __name__ == "__main__":
    unittest.main()
