import unittest

from quality_of_life.devices.fake_provider import FakePhoneProvider
from quality_of_life.devices.models import DeviceCapability, DeviceState
from quality_of_life.devices.runtime import DeviceTool
from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.runtime import JarvisRuntime


DEVICE_CAPS = frozenset({
    Capability.DEVICE_READ,
    Capability.DEVICE_SCREEN,
    Capability.DEVICE_INPUT,
    Capability.DEVICE_NOTIFICATIONS,
    Capability.DEVICE_FILES,
    Capability.DEVICE_APPS,
    Capability.DEVICE_AUTOMATION,
})

PROVIDER_CAPS = frozenset({
    DeviceCapability.STATE_READ,
    DeviceCapability.SCREEN_VIEW,
    DeviceCapability.INPUT_CONTROL,
    DeviceCapability.NOTIFICATION_READ,
    DeviceCapability.FILES,
    DeviceCapability.APP_CONTROL,
})


class PromotedPhoneIntegrationTests(unittest.TestCase):
    def make_tool(self):
        provider = FakePhoneProvider()
        provider.add_device(DeviceState("phone-1", "Main Phone", True, 90, True, "fake"), PROVIDER_CAPS)
        provider.add_device(DeviceState("phone-2", "Spare Phone", True, 40, False, "fake"), PROVIDER_CAPS)
        policy = CapabilityPolicy(allowed=DEVICE_CAPS)
        tool = DeviceTool(policy, providers=(provider,))
        return tool, provider

    def test_device_tool_supports_multiple_devices_and_screen_all(self):
        tool, provider = self.make_tool()
        self.assertEqual({d.device_id for d in tool.list()}, {"phone-1", "phone-2"})
        self.assertTrue(tool.select("phone-2").ok)
        self.assertEqual(tool.active().data["state"].device_id, "phone-2")
        results = tool.screen_all()
        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.ok for result in results))
        self.assertEqual({op[1] for op in provider.operations if op[0] == "screen"}, {"phone-1", "phone-2"})

    def test_jarvis_runtime_handles_phone_list_and_screen_all_intents(self):
        tool, _ = self.make_tool()
        policy = CapabilityPolicy(allowed=DEVICE_CAPS)
        runtime = JarvisRuntime(policy, factories={"devices": lambda: tool})
        listed = runtime.handle_text("show my phones")
        self.assertEqual(listed["intent"].kind, "device_list")
        self.assertEqual(len(listed["result"]), 2)
        all_screens = runtime.handle_text("show all my phones")
        self.assertEqual(all_screens["intent"].kind, "device_screen_all")
        self.assertEqual(len(all_screens["result"]), 2)

    def test_device_input_remains_confirmation_gated(self):
        tool, _ = self.make_tool()
        no_confirmation = CapabilityPolicy(allowed=DEVICE_CAPS)
        with self.assertRaises(PermissionError):
            tool.input("phone-1", "tap", x=100, y=200)
        self.assertTrue(tool.input("phone-1", "tap", x=100, y=200, confirmed=True).ok)


if __name__ == "__main__":
    unittest.main()
