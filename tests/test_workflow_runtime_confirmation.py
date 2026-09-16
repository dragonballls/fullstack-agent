import unittest
from unittest.mock import Mock

from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.workflows import Workflow, WorkflowService, WorkflowStep


class RuntimeConfirmationTests(unittest.TestCase):
    def test_confirmed_execution_passes_confirmation_to_runtime(self):
        runtime = Mock()
        runtime.policy = CapabilityPolicy(
            allowed=frozenset({Capability.APP_LAUNCH}),
            require_confirmation=frozenset({Capability.APP_LAUNCH}),
        )
        runtime.dispatch.return_value = "ok"
        workflow = Workflow.new("Launch", steps=(WorkflowStep("computer.open_app", {"command": "example"}),))
        result = WorkflowService.execute(runtime, workflow, confirmed=True)
        self.assertTrue(result.verified)
        runtime.dispatch.assert_called_once_with(
            Capability.APP_LAUNCH,
            "computer.open_app",
            command="example",
            confirmed=True,
        )


if __name__ == "__main__":
    unittest.main()
