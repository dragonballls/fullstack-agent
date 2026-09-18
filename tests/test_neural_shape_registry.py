import unittest
from tempfile import TemporaryDirectory

from quality_of_life.neural_shapes import ShapeRegistry


class ShapeRegistryTests(unittest.TestCase):
    def test_custom_shape_round_trip(self):
        with TemporaryDirectory() as tmp:
            reg = ShapeRegistry(tmp + "/shapes.json")
            saved = reg.save("my-star", {"name":"star","family":"freeform","parameters":{"points":7}})
            self.assertEqual(reg.resolve("my-star").parameters["points"], 7.0)
            self.assertEqual(reg.catalog()[0]["name"], "my-star")
            reg2 = ShapeRegistry(tmp + "/shapes.json")
            self.assertEqual(reg2.resolve("my-star").name, "star")

    def test_delete(self):
        with TemporaryDirectory() as tmp:
            reg=ShapeRegistry(tmp + "/shapes.json")
            reg.save("x", "spiral")
            self.assertTrue(reg.delete("x"))
            self.assertIsNone(reg.get("x"))


if __name__ == "__main__":
    unittest.main()
