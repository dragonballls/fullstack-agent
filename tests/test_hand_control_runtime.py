from quality_of_life.hand_control_runtime import HandControlRuntime


class FakePyAutoGUI:
    def mouseUp(self):
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


def test_hand_control_runtime_starts_disabled_and_is_idempotent():
    runtime = HandControlRuntime(controller=FakeController())
    assert runtime.enabled is False
    assert runtime.start() is True
    assert runtime.enabled is True
    assert runtime.start() is True
    runtime.stop()
    assert runtime.enabled is False


def test_hand_control_runtime_reports_local_tracker_url():
    runtime = HandControlRuntime(controller=FakeController())
    assert runtime.url == "http://127.0.0.1:8795/"
    runtime.stop()
