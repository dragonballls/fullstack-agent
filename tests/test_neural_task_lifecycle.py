import unittest

from quality_of_life.neural_world import NeuralWorld
from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.runtime import JarvisRuntime


class TaskNeuronLifecycleTests(unittest.TestCase):
    def test_confirmation_request_stays_waiting(self):
        runtime = JarvisRuntime.__new__(JarvisRuntime)
        runtime._neural_world_service = NeuralWorld()
        task_id = runtime.neural_task_started("open application")
        runtime.neural_task_update(task_id, status="waiting", step="Waiting for confirmation", progress=28)
        entity = runtime._neural_world_service._entities[task_id]
        self.assertEqual(entity.lifecycle.value, "waiting")
        self.assertEqual(entity.status, "Waiting for confirmation")

    def test_completed_task_becomes_mature(self):
        runtime = JarvisRuntime.__new__(JarvisRuntime)
        runtime._neural_world_service = NeuralWorld()
        task_id = runtime.neural_task_started("inspect system")
        runtime.neural_task_finished(task_id, success=True, message="verified")
        entity = runtime._neural_world_service._entities[task_id]
        self.assertEqual(entity.lifecycle.value, "mature")
        self.assertEqual(entity.status, "succeeded")

if __name__ == "__main__":
    unittest.main()
