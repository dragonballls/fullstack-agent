import unittest
from pathlib import Path
from unittest.mock import Mock

from quality_of_life.browser import BrowserController
from quality_of_life.computer import ComputerController
from quality_of_life.permissions import Capability, CapabilityDenied, CapabilityPolicy
from quality_of_life.screen import ScreenCapture


class OptionalAdapterTests(unittest.TestCase):
    def test_computer_rejects_invalid_click_count_before_call(self):
        fake = Mock()
        controller = ComputerController.__new__(ComputerController)
        controller.policy = CapabilityPolicy(allowed=frozenset({Capability.MOUSE_CONTROL}))
        controller.pyautogui = fake
        with self.assertRaises(ValueError):
            controller.click(clicks=4)
        fake.click.assert_not_called()

    def test_computer_checks_permission_before_input(self):
        fake = Mock()
        controller = ComputerController.__new__(ComputerController)
        controller.policy = CapabilityPolicy()
        controller.pyautogui = fake
        with self.assertRaises(CapabilityDenied):
            controller.click()
        fake.click.assert_not_called()

    def test_screen_capture_checks_permission_before_dependency(self):
        fake_mss = Mock()
        capture = ScreenCapture(CapabilityPolicy(), mss_module=fake_mss)
        with self.assertRaises(CapabilityDenied):
            capture.capture()
        fake_mss.mss.assert_not_called()

    def test_screen_capture_uses_injected_backend(self):
        shot = Mock()
        shot.rgb = b"rgb"
        shot.size = (1, 1)
        session = Mock()
        session.__enter__.return_value = session
        session.__exit__.return_value = False
        session.monitors = [None, {"left": 0, "top": 0, "width": 1, "height": 1}]
        session.grab.return_value = shot
        fake_mss = Mock()
        fake_mss.mss.return_value = session
        capture = ScreenCapture(
            CapabilityPolicy(allowed=frozenset({Capability.SCREEN_READ})),
            mss_module=fake_mss,
        )
        self.assertEqual(capture.capture(), b"rgb")
        session.grab.assert_called_once()

    def test_browser_rejects_non_http_urls(self):
        controller = BrowserController(CapabilityPolicy(allowed=frozenset({Capability.BROWSER_CONTROL})))
        with self.assertRaises(ValueError):
            controller.open_url("file:///C:/Windows/System32/cmd.exe")

    def test_browser_close_is_idempotent(self):
        controller = BrowserController(CapabilityPolicy())
        controller.close()
        controller.close()


if __name__ == "__main__":
    unittest.main()
