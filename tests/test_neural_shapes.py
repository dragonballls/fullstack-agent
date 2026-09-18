import unittest

from quality_of_life.neural_shapes import BUILTIN_SHAPES, normalize_shape


class ShapeTests(unittest.TestCase):
    def test_builtin(self):
        self.assertIn("droplet", BUILTIN_SHAPES)
        self.assertEqual(normalize_shape("crystal").family, "primitive")

    def test_freeform_name(self):
        shape = normalize_shape("dragon-head")
        self.assertEqual(shape.name, "dragon-head")
        self.assertEqual(shape.family, "freeform")

    def test_parametric(self):
        shape = normalize_shape({"name": "spiral", "family": "parametric", "parameters": {"turns": 3}})
        self.assertEqual(shape.parameters["turns"], 3.0)

    def test_invalid_family(self):
        with self.assertRaises(ValueError):
            normalize_shape({"name": "x", "family": "bad"})


if __name__ == "__main__":
    unittest.main()
