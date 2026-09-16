import unittest

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


class HandControlJarvisTests(unittest.TestCase):
    def make_runtime(self):
        fake = FakeHandRuntime()
        runtime = JarvisRuntime(
            CapabilityPolicy(allowed=frozenset({Capability.MOUSE_CONTROL})),
            confirmation=lambda *_: True,
            factories={"hand_control_runtime": lambda: fake},
        )
        return runtime, fake

    def test_runtime_exposes_hand_control_start_stop(self):
        runtime, fake = self.make_runtime()
        result = runtime.dispatch(Capability.MOUSE_CONTROL, "hand_control.start")
        self.assertEqual(result["started"], True)
        self.assertTrue(fake.enabled)
        runtime.dispatch(Capability.MOUSE_CONTROL, "hand_control.stop")
        self.assertFalse(fake.enabled)

    def test_text_commands_route_to_hand_control(self):
        runtime, _fake = self.make_runtime()
        intent = parse_intent("turn on hand control")
        self.assertEqual(intent.kind, "hand_control_start")
        result = runtime.handle_text("turn on hand control")
        self.assertTrue(result["result"]["enabled"])


if __name__ == "__main__":
    unittest.main()
