import time
import unittest

from quality_of_life.orchestration import RequestProfile
from quality_of_life.router import CloudModelRouter, ProviderResult, ProviderTarget


class _MockRouter(CloudModelRouter):
    def __init__(self):
        super().__init__([ProviderTarget("mock", "https://example.com/v1", "MOCK_KEY", "auto")])
        self.calls = []

    def try_target(self, target, messages):
        self.calls.append(time.monotonic())
        time.sleep(0.05)
        return ProviderResult(True, "ok", target.name, 50)


class OmniRouteLatencyTests(unittest.TestCase):
    def test_complete_many_runs_independent_requests_concurrently(self):
        router = _MockRouter()
        requests = [
            ([{"role": "user", "content": "a"}], RequestProfile.FAST),
            ([{"role": "user", "content": "b"}], RequestProfile.FAST),
            ([{"role": "user", "content": "c"}], RequestProfile.FAST),
        ]
        started = time.monotonic()
        results = router.complete_many(requests, max_parallel=3)
        elapsed = time.monotonic() - started
        self.assertEqual(len(results), 3)
        self.assertLess(elapsed, 0.12)
        self.assertGreaterEqual(len(router.calls), 3)

    def test_profiled_router_exposes_provider_latency(self):
        router = _MockRouter()
        text, provider = router.complete_profiled(
            [{"role": "user", "content": "hello"}], RequestProfile.FAST
        )
        self.assertEqual((text, provider), ("ok", "mock"))
        self.assertGreaterEqual(router.provider_latency_ms("mock", RequestProfile.FAST), 0)


if __name__ == "__main__":
    unittest.main()
