import threading
import unittest

from quality_of_life.agent_orchestrator import AgentOrchestrator
from quality_of_life.orchestration import RequestProfile
from quality_of_life.permissions import Capability


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


class FakeRuntime:
    def __init__(self, execute_result=None):
        self.execute_result = execute_result
        self.dispatch_calls = []

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
        runtime = FakeRuntime(FakeResult("coding branch ready"))
        result = AgentOrchestrator(router, runtime).execute("implement the fix and run the tests")
        self.assertTrue(result.needs_confirmation)
        self.assertEqual(runtime.dispatch_calls, [])

    def test_confirmed_coding_handoff_uses_guarded_self_coding_action(self):
        router = FakeRouter()
        runtime = FakeRuntime(FakeResult("agent/self-code/verified"))
        result = AgentOrchestrator(router, runtime).execute("implement the fix and run the tests", confirmed=True)
        self.assertTrue(runtime.dispatch_calls)
        self.assertEqual(runtime.dispatch_calls[-1][0], Capability.REPO_WRITE)
        self.assertEqual(runtime.dispatch_calls[-1][1], "self_coding.run")
        self.assertTrue(result.verified)

    def test_stream_starts_with_local_ack_and_ends_with_result(self):
        events = list(AgentOrchestrator(FakeRouter(), FakeRuntime()).execute_stream("diagnose my PC"))
        self.assertEqual(events[0].kind, "ack")
        self.assertEqual(events[-1].kind, "result")
        self.assertTrue(any(event.kind == "progress" for event in events))


if __name__ == "__main__":
    unittest.main()
