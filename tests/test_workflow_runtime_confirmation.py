import unittest
from unittest.mock import Mock

from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.workflows import Workflow, WorkflowService, WorkflowStep


class RuntimeConfirmationTests(unittest.TestCase):
    def test_unconfirmed_protected_execution_is_not_dispatched(self):
        runtime = Mock()
        runtime.policy = CapabilityPolicy(
            allowed=frozenset({Capability.APP_LAUNCH}),
            require_confirmation=frozenset({Capability.APP_LAUNCH}),
        )
        workflow = Workflow.new("Launch", steps=(WorkflowStep("computer.open_app", {"command": "example"}),))
        result = WorkflowService.execute(runtime, workflow, confirmed=False)
        self.assertFalse(result.verified)
        self.assertTrue(result.needs_confirmation)
        runtime.dispatch.assert_not_called()
        runtime.orchestrator.run.assert_not_called()

    def test_confirmed_execution_uses_the_guarded_dispatcher_confirmation_hook(self):
        runtime = Mock()
        runtime.policy = CapabilityPolicy(
            allowed=frozenset({Capability.APP_LAUNCH}),
            require_confirmation=frozenset({Capability.APP_LAUNCH}),
        )
        runtime.orchestrator.run.return_value = "ok"
        workflow = Workflow.new("Launch", steps=(WorkflowStep("computer.open_app", {"command": "example"}),))
        result = WorkflowService.execute(runtime, workflow, confirmed=True)
        self.assertTrue(result.verified)
        runtime.orchestrator.run.assert_called_once()
        call = runtime.orchestrator.run.call_args
        self.assertEqual(call.args[:2], (Capability.APP_LAUNCH, "computer.open_app"))
        self.assertEqual(call.kwargs["command"], "example")
        self.assertTrue(call.kwargs["confirmation"](Capability.APP_LAUNCH, "computer.open_app"))


if __name__ == "__main__":
    unittest.main()
