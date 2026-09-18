import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from quality_of_life.neural_shape_controller import NeuralShapeController, parse_rotation_speed
from quality_of_life.neural_world import EntityKind, NeuralWorld
from quality_of_life.spatial_layout import SpatialLayoutStore


class NeuralShapeControllerTests(unittest.TestCase):
    def make_controller(self):
        tmp = TemporaryDirectory()
        world = NeuralWorld(persistence=None)
        layout = SpatialLayoutStore(Path(tmp.name) / "layout.json")
        controller = NeuralShapeController(world, layout, Path(tmp.name) / "history.json")
        return tmp, world, layout, controller

    def test_create_persists_and_records_generated_object_for_remove(self):
        tmp, world, layout, controller = self.make_controller()
        self.addCleanup(tmp.cleanup)
        result = controller.create("Test Globe", "globe", position=(1, 2, 3), rotation_speed=2.0)
        self.assertTrue(result["created"])
        node = world.search("Test Globe", limit=1)[0]
        self.assertEqual(node["shape"]["name"], "sphere")
        self.assertEqual(node["metadata"]["shape_transform"]["angular_velocity"], [0.0, 2.0, 0.0])
        removed = controller.remove(node["id"])
        self.assertTrue(removed["reverted"])
        self.assertEqual(world.search("Test Globe", limit=5), [])

    def test_apply_to_window_records_original_layout_and_restores_it(self):
        tmp, world, layout, controller = self.make_controller()
        self.addCleanup(tmp.cleanup)
        world.upsert("window:77", EntityKind.WINDOW, "Opera GX", source="windows", shape="cube")
        layout.upsert("window:77", shape={"name": "cube", "family": "primitive", "parameters": {}}, rotation=[0, 0, 0])
        changed = controller.apply("window:77", "globe", rotation_speed=1.5)
        self.assertEqual(changed["shape"]["name"], "globe")
        self.assertEqual(layout.get("window:77").shape["name"], "globe")
        self.assertEqual(layout.get("window:77").angular_velocity, (0.0, 1.5, 0.0))
        restored = controller.revert("window:77")
        self.assertTrue(restored["reverted"])
        self.assertEqual(world.search("Opera GX", limit=1)[0]["shape"]["name"], "cube")
        self.assertEqual(layout.get("window:77").shape["name"], "cube")
        self.assertEqual(layout.get("window:77").angular_velocity, (0.0, 0.0, 0.0))

    def test_brain_scope_changes_neural_elements_and_revert_all_restores_them(self):
        tmp, world, layout, controller = self.make_controller()
        self.addCleanup(tmp.cleanup)
        world.upsert("neuron:a", EntityKind.TASK, "Neuron A", source="test", shape="droplet")
        world.upsert("neuron:b", EntityKind.PAGE, "Neuron B", source="test", shape="droplet")
        result = controller.apply_to_scope("brain structure", "sphere", rotation_speed=0.5)
        self.assertGreaterEqual(result["changed"], 2)
        self.assertEqual(world.search("Neuron A", limit=1)[0]["shape"]["name"], "sphere")
        self.assertEqual(world.search("Neuron B", limit=1)[0]["shape"]["name"], "sphere")
        restored = controller.revert_all()
        self.assertTrue(restored["ok"])
        self.assertEqual(world.search("Neuron A", limit=1)[0]["shape"]["name"], "droplet")
        self.assertEqual(world.search("Neuron B", limit=1)[0]["shape"]["name"], "droplet")

    def test_revert_all_also_removes_generated_objects(self):
        tmp, world, layout, controller = self.make_controller()
        self.addCleanup(tmp.cleanup)
        world.upsert("neuron:global", EntityKind.TASK, "Global Neuron", source="test", shape="droplet")
        controller.apply("neuron:global", "heart")
        created = controller.create("Generated Widget", "torus")
        result = controller.revert_all()
        self.assertTrue(result["ok"])
        self.assertEqual(world.search("Global Neuron", limit=1)[0]["shape"]["name"], "droplet")
        self.assertEqual(world.search("Generated Widget", limit=5), [])

    def test_window_without_prior_layout_has_no_layout_after_revert(self):
        tmp, world, layout, controller = self.make_controller()
        self.addCleanup(tmp.cleanup)
        world.upsert("window:88", EntityKind.WINDOW, "Browser Tab", source="windows", shape="cube")
        self.assertIsNone(layout.get("window:88"))
        controller.apply("window:88", "globe", rotation_speed=1.0)
        self.assertIsNotNone(layout.get("window:88"))
        self.assertTrue(controller.revert("window:88")["reverted"])
        self.assertIsNone(layout.get("window:88"))

    def test_builtin_globe_keeps_named_shape_identity(self):
        from quality_of_life.neural_shapes import normalize_shape
        spec = normalize_shape("globe")
        self.assertEqual(spec.name, "globe")
        self.assertEqual(spec.family, "primitive")

    def test_rotation_units_are_normalized(self):
        self.assertAlmostEqual(parse_rotation_speed(30, "degrees per second"), 0.5235987756, places=6)
        self.assertAlmostEqual(parse_rotation_speed(2, "rps"), 12.5663706144, places=6)
        self.assertAlmostEqual(parse_rotation_speed(60, "rpm"), 6.2831853072, places=6)

    def test_shape_history_survives_controller_restart(self):
        tmp, world, layout, controller = self.make_controller()
        self.addCleanup(tmp.cleanup)
        world.upsert("neuron:restart", EntityKind.TASK, "Restart Neuron", source="test", shape="droplet")
        controller.apply("neuron:restart", "heart")
        history_file = Path(tmp.name) / "history.json"
        second = NeuralShapeController(world, layout, history_file)
        self.assertEqual(len(second.history()), 1)
        self.assertTrue(second.revert("neuron:restart")["reverted"])


class ShapeIntentTests(unittest.TestCase):
    def test_requested_phrases_parse(self):
        from quality_of_life.intents import parse_intent

        command = parse_intent("make this browser tab into the shape of a globe and give it a rotational speed 2 radians per second on y")
        self.assertEqual(command.kind, "neural_shape")
        self.assertEqual(command.arguments["target"], "this browser tab")
        self.assertEqual(command.arguments["shape"], "globe")
        self.assertEqual(command.arguments["rotation_axis"], "y")
        self.assertEqual(command.arguments["rotation_unit"], "radians per second")
        self.assertEqual(command.arguments["rotation_speed"], 2.0)

        remove = parse_intent("remove it")
        self.assertEqual(remove.kind, "neural_shape_remove")

        revert = parse_intent("revert this to original state")
        self.assertEqual(revert.kind, "neural_shape_revert")
        self.assertEqual(revert.arguments["target"], "this")

        brain = parse_intent("revert everything to original state")
        self.assertEqual(brain.kind, "neural_shape_revert_all")

        create = parse_intent("create a glowing torus called Halo")
        self.assertEqual(create.kind, "neural_shape_create")
        self.assertEqual(create.arguments["shape"], "glowing torus")
        self.assertEqual(create.arguments["name"], "Halo")


if __name__ == "__main__":
    unittest.main()
