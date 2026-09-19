import unittest
from quality_of_life.neural_world import EntityKind, LifecycleState, NeuralWorld, PerformanceGovernor


class NeuralWorldTests(unittest.TestCase):
    def test_bootstrap_includes_persistent_neural_command_anchor(self):
        from quality_of_life.neural_world import EntityKind, NeuralWorld

        world = NeuralWorld(persistence=None)
        snapshot = world.snapshot(limit=100)
        command = next(item for item in snapshot["entities"] if item["id"] == "jarvis.neural-command")

        self.assertEqual(command["kind"], EntityKind.SUBSYSTEM.value)
        self.assertTrue(command["persistent"])
        self.assertTrue(command["visible"])
        self.assertEqual(command["parent_id"], "jarvis.core")
        self.assertEqual(command["metadata"]["ui_surface"], "neural_command")
        self.assertTrue(command["metadata"]["always_visible"])
        self.assertTrue(any(
            rel["source"] == "jarvis.core"
            and rel["target"] == "jarvis.neural-command"
            and rel["relation_type"] == "neural-command-surface"
            for rel in snapshot["relations"]
        ))

    def test_bootstrap_core_and_subsystems(self):
        world = NeuralWorld()
        snapshot = world.snapshot()
        ids = {item["id"] for item in snapshot["entities"]}
        self.assertIn("jarvis.core", ids)
        self.assertIn("jarvis.browser", ids)
        self.assertGreaterEqual(snapshot["counts"]["relations"], 8)

    def test_subsystems_use_stable_orbital_positions(self):
        world = NeuralWorld()
        snapshot = world.snapshot(limit=100)
        nodes = {item["id"]: item for item in snapshot["entities"]}
        core = nodes["jarvis.core"]["position"]
        for entity_id in ("jarvis.browser", "jarvis.coding", "jarvis.system", "jarvis.gods-eye", "jarvis.workflows", "jarvis.memory", "jarvis.agents", "jarvis.devices"):
            pos = nodes[entity_id]["position"]
            self.assertGreater(((pos[0]-core[0])**2 + (pos[1]-core[1])**2 + (pos[2]-core[2])**2) ** 0.5, 3.5)
            self.assertLess(((pos[0]-core[0])**2 + (pos[1]-core[1])**2 + (pos[2]-core[2])**2) ** 0.5, 6.5)

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
