import unittest
from tempfile import TemporaryDirectory

from quality_of_life.neural_persistence import CURRENT_SCHEMA_VERSION, NeuralPersistence

class PersistenceTests(unittest.TestCase):
    def test_round_trip(self):
        with TemporaryDirectory() as tmp:
            store=NeuralPersistence(tmp)
            store.save([{"id":"a","persistent":True}],[{"source":"a","target":"b"}])
            snap=store.load()
            self.assertIsNotNone(snap)
            self.assertEqual(snap.schema_version,CURRENT_SCHEMA_VERSION)
            self.assertEqual(store.backup().name,"world.backup.json")

if __name__=="__main__":
    unittest.main()
