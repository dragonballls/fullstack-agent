import unittest

from quality_of_life.permissions import CapabilityPolicy
from quality_of_life.runtime import JarvisRuntime
from quality_of_life.activity import ActivityStatus


class RuntimeActivityTests(unittest.TestCase):
    def test_runtime_owns_one_activity_store(self):
        runtime = JarvisRuntime(CapabilityPolicy())

        self.assertIs(runtime.activity_store(), runtime.activity_store())

    def test_activity_snapshot_is_json_safe(self):
        runtime = JarvisRuntime(CapabilityPolicy())
        record = runtime.activity_store().create("Inspect system")

        snapshot = runtime.activity_snapshot()

        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot[0]["id"], record.id)
        self.assertEqual(snapshot[0]["status"], ActivityStatus.QUEUED.value)
        self.assertIn("created_at", snapshot[0])
        self.assertIn("updated_at", snapshot[0])

    def test_cancel_request_does_not_claim_acknowledgement(self):
        runtime = JarvisRuntime(CapabilityPolicy())
        record = runtime.activity_store().create("Long task")
        runtime.activity_store().update(record.id, status=ActivityStatus.RUNNING)

        result = runtime.activity_cancel(record.id)
        observed = runtime.activity_store().get(record.id)

        self.assertEqual(result["status"], ActivityStatus.RUNNING.value)
        self.assertTrue(result["cancel_requested"])
        self.assertEqual(observed.status, ActivityStatus.RUNNING)
        self.assertTrue(observed.cancel_requested)


if __name__ == "__main__":
    unittest.main()
