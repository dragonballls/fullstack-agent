import threading
import unittest

from quality_of_life.agent_orchestrator import AgentOrchestrator
from quality_of_life.orchestration import RequestProfile


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
            prompt = messages[-1]["content"]
            return f"answer:{prompt}", "fake"
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
    def __init__(self):
        self.mutating_calls = 0


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

    def test_mutating_request_is_not_executed_by_model_layer(self):
        router = FakeRouter()
        runtime = FakeRuntime()
        result = AgentOrchestrator(router, runtime).execute("close this application")
        self.assertTrue(result.needs_confirmation)
        self.assertEqual(runtime.mutating_calls, 0)

    def test_stream_starts_with_local_ack_and_ends_with_result(self):
        events = list(AgentOrchestrator(FakeRouter(), FakeRuntime()).execute_stream("diagnose my PC"))
        self.assertEqual(events[0].kind, "ack")
        self.assertEqual(events[-1].kind, "result")
        self.assertTrue(any(event.kind == "progress" for event in events))


if __name__ == "__main__":
    unittest.main()
