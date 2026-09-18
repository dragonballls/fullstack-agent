import unittest

from quality_of_life.neural_events import NeuralEventBus


class NeuralEventTests(unittest.TestCase):
    def test_incremental_sequence_reads(self):
        bus = NeuralEventBus()
        bus.publish("entity.created", entity_id="a")
        bus.publish("entity.active", entity_id="a")
        self.assertEqual([item["sequence"] for item in bus.since(1)], [2])


if __name__ == "__main__":
    unittest.main()
