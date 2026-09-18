import unittest

from quality_of_life.neural_performance import AdaptivePerformanceController


class AdaptivePerformanceTests(unittest.TestCase):
    def test_background_is_minimal(self):
        controller = AdaptivePerformanceController()
        controller.set_mode("background")
        snapshot = controller.snapshot(force=True)
        self.assertEqual(snapshot["quality"], "minimal")
        self.assertEqual(snapshot["particle_cap"], 0)
        self.assertEqual(snapshot["physics_level"], 0)

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            AdaptivePerformanceController().set_mode("invalid")

if __name__ == "__main__":
    unittest.main()
