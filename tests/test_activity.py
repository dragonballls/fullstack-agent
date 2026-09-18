import unittest

from quality_of_life.activity import ActivityCapacityError, ActivityStatus, ActivityStore


class ActivityStoreTests(unittest.TestCase):
    def test_new_activity_is_queued_with_stable_id(self):
        store = ActivityStore()
        record = store.create("Build Jarvis")

        self.assertTrue(record.id)
        self.assertEqual(record.status, ActivityStatus.QUEUED)
        self.assertEqual(record.title, "Build Jarvis")
        self.assertIsNone(record.progress)

    def test_lifecycle_updates_preserve_id(self):
        store = ActivityStore()
        created = store.create("Verify release")

        running = store.update(created.id, status=ActivityStatus.RUNNING, progress=10, step="Starting")
        succeeded = store.update(created.id, status=ActivityStatus.SUCCEEDED, progress=100, step="Complete")

        self.assertEqual(running.id, created.id)
        self.assertEqual(succeeded.id, created.id)
        self.assertEqual(succeeded.progress, 100)
        self.assertEqual(succeeded.step, "Complete")

    def test_progress_is_bounded(self):
        store = ActivityStore()
        record = store.create("Bounded progress")

        high = store.update(record.id, status=ActivityStatus.RUNNING, progress=250)
        low = store.update(record.id, status=ActivityStatus.RUNNING, progress=-20)

        self.assertEqual(high.progress, 100)
        self.assertEqual(low.progress, 0)

    def test_cancellation_requires_acknowledgement(self):
        store = ActivityStore()
        record = store.create("Long task")
        store.update(record.id, status=ActivityStatus.RUNNING)

        requested = store.request_cancel(record.id)
        self.assertEqual(requested.status, ActivityStatus.RUNNING)
        self.assertTrue(requested.cancel_requested)

        acknowledged = store.acknowledge_cancel(record.id)
        self.assertEqual(acknowledged.status, ActivityStatus.CANCELLED)
        self.assertTrue(acknowledged.cancel_requested)

    def test_terminal_status_cannot_be_reactivated(self):
        store = ActivityStore()
        record = store.create("One shot")
        store.update(record.id, status=ActivityStatus.SUCCEEDED)

        with self.assertRaises(ValueError):
            store.update(record.id, status=ActivityStatus.RUNNING)

    def test_store_is_bounded(self):
        store = ActivityStore(max_records=2)
        first = store.create("first")
        second = store.create("second")

        with self.assertRaises(ActivityCapacityError):
            store.create("third")

        self.assertIsNotNone(store.get(first.id))
        self.assertIsNotNone(store.get(second.id))

        store.update(first.id, status=ActivityStatus.SUCCEEDED, progress=100)
        third = store.create("third")

        self.assertIsNone(store.get(first.id))
        self.assertIsNotNone(store.get(second.id))
        self.assertIsNotNone(store.get(third.id))
        self.assertEqual([r.title for r in store.list()], ["third", "second"])

    def test_failed_activity_redacts_common_secret_patterns(self):
        store = ActivityStore()
        record = store.create("Protected operation")
        store.update(record.id, status=ActivityStatus.RUNNING)

        failed = store.update(
            record.id,
            status=ActivityStatus.FAILED,
            error="token=SECRET123 authorization=Bearer SECRET456",
        )

        self.assertNotIn("SECRET123", failed.error)
        self.assertNotIn("SECRET456", failed.error)
        self.assertIn("[redacted]", failed.error)



if __name__ == "__main__":
    unittest.main()
