import unittest

from quality_of_life.neural_observation import NeuralObservationController


class ObservationTests(unittest.TestCase):
    def test_off_by_default(self):
        self.assertFalse(NeuralObservationController().snapshot()["enabled"])

    def test_start_stop(self):
        controller = NeuralObservationController()
        state = controller.start("coding", "show me what you are doing")
        self.assertTrue(state["enabled"])
        self.assertEqual(state["focus"], "coding")
        self.assertFalse(controller.stop()["enabled"])

    def test_invalid_focus(self):
        with self.assertRaises(ValueError):
            NeuralObservationController().start("private")


if __name__ == "__main__":
    unittest.main()
