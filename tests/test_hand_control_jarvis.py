from quality_of_life.intents import parse_intent
from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.runtime import JarvisRuntime


class FakeHandRuntime:
    def __init__(self):
        self.enabled = False
        self.url = "http://127.0.0.1:8795/"

    def start(self):
        self.enabled = True
        return True

    def stop(self):
        self.enabled = False

    def status(self):
        return {"enabled": self.enabled, "url": self.url}


def test_runtime_exposes_hand_control_start_stop():
    fake = FakeHandRuntime()
    runtime = JarvisRuntime(
        CapabilityPolicy(allowed=frozenset({Capability.MOUSE_CONTROL})),
        confirmation=lambda *_: True,
        factories={"hand_control_runtime": lambda: fake},
    )
    assert runtime.dispatch(Capability.MOUSE_CONTROL, "hand_control.start") is True
    assert fake.enabled is True
    runtime.dispatch(Capability.MOUSE_CONTROL, "hand_control.stop")
    assert fake.enabled is False


def test_text_commands_route_to_hand_control():
    fake = FakeHandRuntime()
    runtime = JarvisRuntime(
        CapabilityPolicy(allowed=frozenset({Capability.MOUSE_CONTROL})),
        confirmation=lambda *_: True,
        factories={"hand_control_runtime": lambda: fake},
    )
    intent = parse_intent("turn on hand control")
    assert intent.kind == "hand_control_start"
    result = runtime.handle_text("turn on hand control")
    assert result["result"]["enabled"] is True
