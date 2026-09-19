import tempfile
import threading
import unittest

from quality_of_life.activity import ActivityStatus, ActivityStore
from quality_of_life.agent_orchestrator import AgentOrchestrator
from quality_of_life.orchestration import RequestProfile
from quality_of_life.permissions import Capability
from quality_of_life.workflows import Workflow, WorkflowService, WorkflowStep, WorkflowStore


class FakeOperation:
    def __init__(self, success=True, verified=True):
        self.success = success
        self.verified = verified


class FakeResult:
    def __init__(self, text="tool-result", results=None):
        self.message = text
        self.verified = True
        self.results = tuple(results or ())


class FakeRouter:
    def __init__(self):
        self.calls = []
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def complete_profiled(self, messages, profile):
        with self.lock:
            self.calls.append((messages, profile))
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            return f"answer:{messages[-1]['content']}", "fake"
        finally:
            with self.lock:
                self.active -= 1

    def complete_many(self, requests, max_parallel=None):
        results = []
        for messages, profile in requests:
            text, target = self.complete_profiled(messages, profile)
            results.append(type("Result", (), {"ok": True, "text": text, "target_name": target, "latency_ms": 1, "error": None})())
        return tuple(results)


class FakeOrchestrator:
    def __init__(self):
        self.actions = {}

    def register(self, action):
        self.actions[getattr(action, "operation", repr(action))] = action


class FakeRuntime:
    def __init__(self, execute_result=None):
        self.execute_result = execute_result
        self.dispatch_calls = []
        self.orchestrator = FakeOrchestrator()
        self.activity = ActivityStore()

        class Policy:
            def needs_confirmation(self, _capability):
                return False

        class Policy:
            def needs_confirmation(self, capability):
                return capability == Capability.FILE_DELETE

        self.policy = Policy()

    def activity_store(self):
        return self.activity

    def dispatch(self, capability, operation, *args, **kwargs):
        self.dispatch_calls.append((capability, operation, args, kwargs))
        return self.execute_result or FakeResult()


class AgentOrchestratorTests(unittest.TestCase):
    def test_fast_request_uses_one_model_call(self):
        router = FakeRouter()
        result = AgentOrchestrator(router, FakeRuntime()).execute("summarize this")
        self.assertEqual(len(router.calls), 1)
        self.assertTrue(result.verified)
        self.assertEqual(result.profile, RequestProfile.FAST.value)

    def test_specialized_request_uses_parallel_specialists_then_synthesis(self):
        router = FakeRouter()
        result = AgentOrchestrator(router, FakeRuntime()).execute("diagnose my PC")
        self.assertEqual(result.profile, RequestProfile.MAINTENANCE.value)
        self.assertEqual(result.parallel_tasks_completed, 2)
        self.assertEqual(len(router.calls), 3)
        self.assertTrue(result.verified)

    def test_neural_shape_mutations_use_guarded_dispatch_and_selection(self):
        router = FakeRouter()
        runtime = FakeRuntime()
        runtime.execute_result = {"ok": True, "created": True, "reverted": True}
        runtime.neural_current_selection = lambda: "window:77"
        agent = AgentOrchestrator(router, runtime)

        _, verified, errors, needs_confirmation = agent._deterministic_context(
            "make it into a sphere",
            confirmed=True,
        )
        self.assertTrue(verified)
        self.assertFalse(errors)
        self.assertFalse(needs_confirmation)
        self.assertEqual(runtime.dispatch_calls[-1][0], Capability.SYSTEM_DIAGNOSTICS)
        self.assertEqual(runtime.dispatch_calls[-1][1], "neural.shape.apply")
        self.assertEqual(runtime.dispatch_calls[-1][3]["target"], "window:77")

        runtime.dispatch_calls.clear()
        _, verified, errors, needs_confirmation = agent._deterministic_context(
            "revert it to original state",
            confirmed=True,
        )
        self.assertTrue(verified)
        self.assertFalse(errors)
        self.assertFalse(needs_confirmation)
        self.assertEqual(runtime.dispatch_calls[-1][1], "neural.shape.revert")
        self.assertEqual(runtime.dispatch_calls[-1][3]["target"], "window:77")

    def test_shape_mutation_without_selection_fails_cleanly(self):
        router = FakeRouter()
        runtime = FakeRuntime()
        runtime.neural_current_selection = lambda: None
        agent = AgentOrchestrator(router, runtime)
        _, verified, errors, _ = agent._deterministic_context("make it into a sphere", confirmed=True)
        self.assertFalse(verified)
        self.assertTrue(errors)
        self.assertEqual(runtime.dispatch_calls, [])

    def test_maintenance_diagnosis_uses_existing_read_only_runtime_action(self):
        router = FakeRouter()
        runtime = FakeRuntime(FakeResult("real diagnostic report"))
        result = AgentOrchestrator(router, runtime).execute("diagnose my PC")
        self.assertEqual(runtime.dispatch_calls[0][0], Capability.SYSTEM_DIAGNOSTICS)
        self.assertEqual(runtime.dispatch_calls[0][1], "windows_maintenance.diagnose")
        self.assertIn("real diagnostic report", router.calls[-1][0][-1]["content"])
        self.assertTrue(result.verified)

    def test_mutating_request_is_not_executed_without_confirmation(self):
        router = FakeRouter()
        runtime = FakeRuntime()
        result = AgentOrchestrator(router, runtime).execute("repair my PC")
        self.assertTrue(result.needs_confirmation)
        self.assertEqual(runtime.dispatch_calls, [])

    def test_confirmed_maintenance_request_uses_guarded_runtime_action(self):
        router = FakeRouter()
        runtime = FakeRuntime(FakeResult("repair verified", [FakeOperation()]))
        result = AgentOrchestrator(router, runtime).execute("repair my PC", confirmed=True)
        self.assertTrue(runtime.dispatch_calls)
        self.assertEqual(runtime.dispatch_calls[-1][0], Capability.SYSTEM_MAINTENANCE)
        self.assertEqual(runtime.dispatch_calls[-1][1], "windows_maintenance.handle")
        self.assertTrue(result.verified)

    def test_coding_handoff_requires_confirmation(self):
        router = FakeRouter()
        runtime = FakeRuntime(FakeResult("coding checkpoint ready"))
        result = AgentOrchestrator(router, runtime).execute("implement the fix and run the tests")
        self.assertTrue(result.needs_confirmation)
        self.assertEqual(runtime.dispatch_calls, [])

    def test_confirmed_coding_handoff_uses_guarded_self_coding_action(self):
        router = FakeRouter()
        runtime = FakeRuntime(FakeResult("agent/checkpoint/verified-123"))
        result = AgentOrchestrator(router, runtime).execute("implement the fix and run the tests", confirmed=True)
        self.assertTrue(runtime.dispatch_calls)
        self.assertEqual(runtime.dispatch_calls[-1][0], Capability.REPO_WRITE)
        self.assertEqual(runtime.dispatch_calls[-1][1], "self_coding.run")
        self.assertTrue(result.verified)
        self.assertIn("checkpoint", result.text.casefold())
        self.assertIn("explicit approval", result.text.casefold())

    def test_stream_starts_with_local_ack_and_ends_with_result(self):
        events = list(AgentOrchestrator(FakeRouter(), FakeRuntime()).execute_stream("diagnose my PC"))
        self.assertEqual(events[0].kind, "ack")
        self.assertEqual(events[-1].kind, "result")
        self.assertTrue(any(event.kind == "progress" for event in events))

    def test_confirmed_coding_handoff_publishes_completed_activity(self):
        router = FakeRouter()
        runtime = FakeRuntime(FakeResult("agent/self-code/verified"))

        result = AgentOrchestrator(router, runtime).execute(
            "implement the fix and run the tests",
            confirmed=True,
        )

        self.assertTrue(result.verified)
        records = runtime.activity.list()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].status, ActivityStatus.SUCCEEDED)
        self.assertEqual(records[0].progress, 100)

    def test_explicit_saved_workflow_command_requires_confirmation(self):
        runtime = FakeRuntime()
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkflowStore(f"{tmp}/workflows.json")
            workflow = Workflow.new(
                "System check",
                aliases=("status check",),
                steps=(WorkflowStep("files.delete", {"path": "x"}),),
            )
            store.create(workflow)
            agent = AgentOrchestrator(FakeRouter(), runtime)
            agent._workflow_store = store

            text, verified, errors, needs_confirmation = agent._deterministic_context(
                "run my system check",
                confirmed=False,
            )

            self.assertTrue(needs_confirmation)
            self.assertFalse(verified)
            self.assertEqual(errors, [])
            self.assertIn("confirmation", text.casefold())
            self.assertEqual(runtime.dispatch_calls, [])

    def test_confirmed_saved_workflow_command_executes_through_runtime(self):
        runtime = FakeRuntime()
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkflowStore(f"{tmp}/workflows.json")
            workflow = Workflow.new(
                "System check",
                steps=(WorkflowStep("applications.list", {}),),
            )
            store.create(workflow)
            agent = AgentOrchestrator(FakeRouter(), runtime)
            agent._workflow_store = store

            text, verified, errors, needs_confirmation = agent._deterministic_context(
                "run my system check",
                confirmed=True,
            )

            self.assertTrue(verified)
            self.assertFalse(needs_confirmation)
            self.assertEqual(errors, [])
            self.assertIn("System check", text)
            self.assertEqual(len(runtime.dispatch_calls), 1)
            self.assertEqual(runtime.dispatch_calls[0][1], "applications.list")

    def test_corrupt_workflow_store_does_not_block_normal_commands(self):
        runtime = FakeRuntime()
        with tempfile.TemporaryDirectory() as tmp:
            path = f"{tmp}/workflows.json"
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{not valid json")
            store = WorkflowStore(path)
            agent = AgentOrchestrator(FakeRouter(), runtime)
            agent._workflow_store = store

            text, verified, errors, needs_confirmation = agent._deterministic_context(
                "list processes",
                confirmed=False,
            )

            self.assertTrue(verified)
            self.assertFalse(needs_confirmation)
            self.assertEqual(errors, [])
            self.assertEqual(len(runtime.dispatch_calls), 1)
            self.assertEqual(runtime.dispatch_calls[0][1], "processes.list")


if __name__ == "__main__":
    unittest.main()
