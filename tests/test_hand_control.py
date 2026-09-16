import unittest

from quality_of_life.hand_control import HandControlBridge, HandEvent, HandGestureInterpreter, HandSample


class FakePyAutoGUI:
    def __init__(self):
        self.calls = []

    def size(self):
        return 1920, 1080

    def mouseDown(self, button="left"):
        self.calls.append(("mouseDown", button))

    def mouseUp(self, button="left"):
        self.calls.append(("mouseUp", button))


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


class HandControlTests(unittest.TestCase):
    def sample(self, **kwargs):
        values = dict(x=0.25, y=0.40, pinch=False, fingers=1, confidence=0.99)
        values.update(kwargs)
        return HandSample(**values)

    def test_pointing_moves_after_deadzone(self):
        interpreter = HandGestureInterpreter(move_deadzone=0.01)
        self.assertEqual(interpreter.interpret(self.sample(), timestamp=0.0)[0].kind, "move")
        self.assertEqual(interpreter.interpret(self.sample(x=0.255), timestamp=0.1), ())
        self.assertEqual(interpreter.interpret(self.sample(x=0.30), timestamp=0.2)[0].kind, "move")

    def test_low_confidence_is_rejected(self):
        interpreter = HandGestureInterpreter()
        self.assertEqual(interpreter.interpret(self.sample(confidence=0.50), timestamp=0.0), ())

    def test_pinch_release_clicks_once(self):
        interpreter = HandGestureInterpreter(click_cooldown_s=0.2)
        interpreter.interpret(self.sample(pinch=False), timestamp=0.0)
        interpreter.interpret(self.sample(pinch=True), timestamp=0.1)
        self.assertEqual([e.kind for e in interpreter.interpret(self.sample(pinch=False), timestamp=0.2)], ["click"])
        interpreter.interpret(self.sample(pinch=True), timestamp=0.3)
        self.assertEqual(interpreter.interpret(self.sample(pinch=False), timestamp=0.35), ())

    def test_pinch_hold_drag_and_release(self):
        interpreter = HandGestureInterpreter(drag_hold_s=0.3, click_cooldown_s=0.0)
        interpreter.interpret(self.sample(), timestamp=0.0)
        interpreter.interpret(self.sample(pinch=True), timestamp=0.1)
        self.assertEqual(interpreter.interpret(self.sample(pinch=True), timestamp=0.4)[0].kind, "drag_start")
        self.assertEqual(interpreter.interpret(self.sample(pinch=False), timestamp=0.5)[0].kind, "drag_end")

    def test_two_finger_motion_scrolls_and_is_bounded(self):
        interpreter = HandGestureInterpreter(move_deadzone=0.01)
        interpreter.interpret(self.sample(fingers=2, y=0.5), timestamp=0.0)
        event = interpreter.interpret(self.sample(fingers=2, y=0.9), timestamp=0.1)[0]
        self.assertEqual(event.kind, "scroll")
        self.assertLessEqual(abs(event.amount), 5)

    def test_fist_requires_debounce_then_pauses(self):
        interpreter = HandGestureInterpreter(pose_debounce_frames=3)
        interpreter.interpret(self.sample(), timestamp=0.0)
        self.assertEqual(interpreter.interpret(self.sample(fingers=0), timestamp=0.1), ())
        self.assertEqual(interpreter.interpret(self.sample(fingers=0), timestamp=0.2), ())
        self.assertEqual(interpreter.interpret(self.sample(fingers=0), timestamp=0.3)[0].kind, "pause")
        self.assertFalse(interpreter.enabled)

    def test_open_palm_resume_requires_stable_frames(self):
        interpreter = HandGestureInterpreter(resume_frames=2)
        interpreter.disable()
        interpreter.interpret(self.sample(fingers=5), timestamp=0.0)
        self.assertEqual(interpreter.interpret(self.sample(fingers=5), timestamp=0.1)[0].kind, "resume")
        self.assertTrue(interpreter.enabled)

    def test_bridge_disabled_by_default(self):
        controller = FakeController()
        bridge = HandControlBridge(controller=controller)
        self.assertFalse(bridge.dispatch(HandEvent(kind="move", x=0.5, y=0.5)))
        self.assertEqual(controller.calls, [])

    def test_bridge_maps_pointer_and_drag(self):
        controller = FakeController()
        bridge = HandControlBridge(enabled=True, controller=controller)
        self.assertTrue(bridge.dispatch(HandEvent(kind="move", x=0.5, y=0.5)))
        bridge.dispatch(HandEvent(kind="drag_start"))
        bridge.dispatch(HandEvent(kind="drag_end"))
        self.assertEqual(controller.calls[0], ("move", 960, 540))
        self.assertEqual(controller.pyautogui.calls, [("mouseDown", "left"), ("mouseUp", "left")])


if __name__ == "__main__":
    unittest.main()
