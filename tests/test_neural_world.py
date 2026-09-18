import unittest
from quality_of_life.neural_world import EntityKind, LifecycleState, NeuralWorld, PerformanceGovernor


class NeuralWorldTests(unittest.TestCase):
    def test_bootstrap_core_and_subsystems(self):
        world = NeuralWorld()
        snapshot = world.snapshot()
        ids = {item["id"] for item in snapshot["entities"]}
        self.assertIn("jarvis.core", ids)
        self.assertIn("jarvis.browser", ids)
        self.assertGreaterEqual(snapshot["counts"]["relations"], 8)

    def test_identity_and_update_are_stable(self):
        world = NeuralWorld()
        first = world.upsert("app:opera", EntityKind.APPLICATION, "Opera GX", source="browser")
        second = world.upsert("app:opera", EntityKind.APPLICATION, "Opera GX", source="browser", status="active")
        self.assertIs(first, second)
        self.assertEqual(second.status, "active")

    def test_lifecycle_retirement(self):
        world = NeuralWorld()
        world.upsert("tmp:1", EntityKind.TEMPORARY, "Temporary", source="task", lifecycle=LifecycleState.NEWBORN)
        self.assertTrue(world.retire("tmp:1"))
        self.assertEqual(world.search("Temporary")[0]["lifecycle"], "retired")

    def test_search_and_trace(self):
        world = NeuralWorld()
        world.upsert("page:1", EntityKind.PAGE, "YouTube", source="browser")
        world.relate("jarvis.browser", "page:1", "opened", 0.8)
        self.assertEqual(world.search("youtube", kind="page")[0]["id"], "page:1")
        self.assertTrue(world.trace("jarvis.core", "page:1"))

    def test_empty_search_rejected(self):
        with self.assertRaises(ValueError):
            NeuralWorld().search(" ")

    def test_snapshot_limit(self):
        world = NeuralWorld(max_entities=200)
        for i in range(100):
            world.upsert("task:%d" % i, EntityKind.TASK, "Task %d" % i, source="task")
        self.assertLessEqual(len(world.snapshot(limit=25)["entities"]), 25)

    def test_performance_mode(self):
        governor = PerformanceGovernor()
        self.assertEqual(governor.set_mode("background"), "background")
        self.assertEqual(governor.sample().quality, "minimal")
        with self.assertRaises(ValueError):
            governor.set_mode("bad")


if __name__ == "__main__":
    unittest.main()
