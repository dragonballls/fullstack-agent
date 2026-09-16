import unittest

from quality_of_life.hand_control_runtime import HandControlRuntime


class FakePyAutoGUI:
    def mouseUp(self, button="left"):
        return None

    def size(self):
        return (1920, 1080)


class FakeController:
    pyautogui = FakePyAutoGUI()

    def move(self, _x, _y):
        return None

    def click(self, button="left", clicks=1):
        return None

    def scroll(self, _amount):
        return None


class HandControlRuntimeTests(unittest.TestCase):
    def test_starts_disabled_is_idempotent_and_stops(self):
        runtime = HandControlRuntime(controller=FakeController(), open_browser=False)
        self.assertFalse(runtime.enabled)
        self.assertEqual(runtime.status()["state"], "disabled")
        self.assertTrue(runtime.start())
        self.assertTrue(runtime.enabled)
        self.assertEqual(runtime.status()["state"], "active")
        self.assertTrue(runtime.start())
        runtime.stop()
        self.assertFalse(runtime.enabled)
        self.assertEqual(runtime.status()["state"], "disabled")

    def test_reports_local_tracker_url(self):
        runtime = HandControlRuntime(controller=FakeController(), open_browser=False)
        self.assertEqual(runtime.url, "http://127.0.0.1:8795/")
        self.assertFalse(runtime.enabled)


if __name__ == "__main__":
    unittest.main()
