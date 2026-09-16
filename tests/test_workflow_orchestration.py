import tempfile
import unittest
from pathlib import Path

from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.workflows import Workflow, WorkflowService, WorkflowStep, WorkflowStore


class FakeDispatcher:
    def __init__(self, allowed=None):
        self.calls = []
        self.allowed = set(allowed or ())

    def run(self, capability, operation, *args, confirmation=None, **kwargs):
        if capability not in self.allowed:
            raise PermissionError(f"Capability is not enabled: {capability.value}")
        if confirmation is not None and not confirmation(capability, operation):
            raise PermissionError(f"Confirmation was denied: {operation}")
        self.calls.append(operation)
        return f"ok:{operation}"


class FakeRuntime:
    def __init__(self, allowed=None, confirm=False):
        self.policy = CapabilityPolicy(allowed=frozenset(allowed or ()), require_confirmation=frozenset())
        self.confirmation = (lambda _capability, _operation: confirm)
        self.orchestrator = FakeDispatcher(allowed=allowed)

    def dispatch(self, capability, operation, *args, **kwargs):
        return self.orchestrator.run(capability, operation, *args, **kwargs)


class WorkflowOrchestrationTests(unittest.TestCase):
    def test_run_named_workflow_executes_steps_in_order(self):
        runtime = FakeRuntime(allowed={Capability.APP_READ, Capability.SYSTEM_DIAGNOSTICS}, confirm=True)
        workflow = Workflow.new(
            "Morning",
            steps=(
                WorkflowStep("applications.list", {}),
                WorkflowStep("system.inspect", {}),
            ),
        )
        result = WorkflowService.execute(runtime, workflow, confirmed=True)
        self.assertTrue(result.verified)
        self.assertEqual(runtime.orchestrator.calls, ["applications.list", "system.inspect"])
        self.assertEqual(result.completed_steps, 2)

    def test_fail_fast_stops_at_first_error(self):
        runtime = FakeRuntime(allowed={Capability.APP_READ}, confirm=True)
        workflow = Workflow.new(
            "Fail",
            steps=(WorkflowStep("applications.list", {}), WorkflowStep("system.inspect", {})),
        )
        result = WorkflowService.execute(runtime, workflow, confirmed=True)
        self.assertFalse(result.verified)
        self.assertEqual(result.completed_steps, 1)
        self.assertEqual(runtime.orchestrator.calls, ["applications.list"])
        self.assertTrue(result.errors)

    def test_continue_on_error_runs_later_steps(self):
        runtime = FakeRuntime(allowed={Capability.APP_READ, Capability.SYSTEM_DIAGNOSTICS}, confirm=True)
        broken = WorkflowStep("system.inspect", {}, continue_on_error=True)
        workflow = Workflow.new("Continue", steps=(broken, WorkflowStep("applications.list", {})))
        result = WorkflowService.execute(runtime, workflow, confirmed=True)
        self.assertFalse(result.verified)
        self.assertEqual(result.completed_steps, 2)
        self.assertEqual(runtime.orchestrator.calls, ["system.inspect", "applications.list"])

    def test_missing_confirmation_does_not_execute_mutating_step(self):
        runtime = FakeRuntime(allowed={Capability.APP_LAUNCH}, confirm=False)
        workflow = Workflow.new("Launch", steps=(WorkflowStep("computer.open_app", {"command": "example"}),))
        result = WorkflowService.execute(runtime, workflow, confirmed=False)
        self.assertFalse(result.verified)
        self.assertTrue(result.needs_confirmation)
        self.assertEqual(runtime.orchestrator.calls, [])

    def test_store_backed_request_resolves_across_instances(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflows.json"
            store = WorkflowStore(path)
            workflow = Workflow.new("Morning Setup", aliases=("morning",), steps=(WorkflowStep("applications.list", {}),))
            store.create(workflow)
            resolved = WorkflowStore(path).resolve("run my morning")
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved.id, workflow.id)


if __name__ == "__main__":
    unittest.main()
