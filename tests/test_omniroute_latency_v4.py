import time
import unittest
from quality_of_life.router import CloudModelRouter, ProviderResult, ProviderTarget
from quality_of_life.orchestration import RequestProfile

class _LatencyRouter(CloudModelRouter):
    def __init__(self):
        super().__init__([ProviderTarget("mock", "https://example.com/v1", "MOCK_KEY", "auto")])
        self.calls = []
    def try_target(self, target, messages):
        self.calls.append(time.monotonic())
        time.sleep(0.03)
        return ProviderResult(True, "ok", target.name, 30)

class TestOmniRouteLatency(unittest.TestCase):
    def test_complete_many_is_concurrent(self):
        router = _LatencyRouter()
        requests = [([{"role":"user","content":str(i)}], RequestProfile.FAST) for i in range(4)]
        started = time.monotonic()
        results = router.complete_many(requests, max_parallel=4)
        elapsed = time.monotonic() - started
        self.assertEqual(len(results), 4)
        self.assertLess(elapsed, 0.08)

    def test_profiled_call_exposes_latency_metric(self):
        router = _LatencyRouter()
        router.complete_profiled([{"role":"user","content":"hello"}], RequestProfile.FAST)
        self.assertGreaterEqual(router.provider_latency_ms("mock", RequestProfile.FAST), 0)
