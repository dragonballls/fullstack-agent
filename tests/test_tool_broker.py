from __future__ import annotations

import time
import unittest

from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.tool_broker import ToolManifest, UniversalToolBroker


class FakeReadAdapter:
    def manifest(self):
        return ToolManifest("fake", "fake adapter", ("web.fetch",))

    def invoke(self, operation, arguments):
        return {"body": arguments.get("body", "ok")}


class FakeWriteAdapter:
    def manifest(self):
        return ToolManifest("writer", "write adapter", ("api.request.write",))

    def invoke(self, operation, arguments):
        return {"ok": True}


class UniversalToolBrokerTests(unittest.TestCase):
    def test_registered_adapter_is_discoverable(self):
        policy = CapabilityPolicy(allowed=frozenset({Capability.SYSTEM_DIAGNOSTICS}))
        broker = UniversalToolBroker(policy=policy)
        broker.register(FakeReadAdapter())
        self.assertEqual(broker.describe("fake").operations, ("web.fetch",))
        self.assertEqual(broker.list_manifests()[0].name, "fake")

    def test_unregistered_operation_is_rejected(self):
        policy = CapabilityPolicy(allowed=frozenset({Capability.SYSTEM_DIAGNOSTICS}))
        broker = UniversalToolBroker(policy=policy)
        result = broker.invoke("web.search", {"query": "x"})
        self.assertFalse(result.ok)
        self.assertIn("no adapter", result.error or "")

    def test_confirmation_is_required_for_external_operation(self):
        policy = CapabilityPolicy(allowed=frozenset({Capability.ACCOUNT_WRITE}))
        broker = UniversalToolBroker(policy=policy)
        broker.register(FakeWriteAdapter())
        result = broker.invoke("api.request.write", {"endpoint": "x", "path": "/v1"})
        self.assertFalse(result.ok)
        self.assertIn("confirmation", result.error or "")

    def test_result_is_bounded(self):
        policy = CapabilityPolicy(allowed=frozenset({Capability.SYSTEM_DIAGNOSTICS}))
        broker = UniversalToolBroker(policy=policy, max_result_chars=1000)
        broker.register(FakeReadAdapter())
        result = broker.invoke("web.fetch", {"body": "x" * 2000})
        self.assertTrue(result.ok)
        self.assertTrue(result.truncated)
        self.assertLessEqual(len(result.data["body"]), 1015)


if __name__ == "__main__":
    unittest.main()
