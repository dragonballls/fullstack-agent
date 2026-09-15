import time
import unittest

from quality_of_life.orchestration import RequestProfile
from quality_of_life.router import CloudModelRouter, ProviderResult, ProviderTarget


class _TimedRouter(CloudModelRouter):
    def __init__(self, delay=0.05, targets=None):
        super().__init__(targets or [ProviderTarget("mock", "https://example.com/v1", "MOCK_KEY", "auto")])
        self.delay = delay
        self.calls = []

    def try_target(self, target, messages):
        self.calls.append((target.name, time.monotonic()))
        time.sleep(self.delay)
        return ProviderResult(True, "ok", target.name, int(self.delay * 1000))


class OmniRouteUltraLatencyTests(unittest.TestCase):
    def setUp(self):
        CloudModelRouter._latency_ewma_ms.clear()
        CloudModelRouter._latency_samples.clear()

    def test_parallel_requests_overlap(self):
        router = _TimedRouter(delay=0.05)
        started = time.monotonic()
        results = router.complete_many(
            [
                ([{"role": "user", "content": "a"}], RequestProfile.FAST),
                ([{"role": "user", "content": "b"}], RequestProfile.FAST),
                ([{"role": "user", "content": "c"}], RequestProfile.FAST),
            ],
            max_parallel=3,
        )
        elapsed = time.monotonic() - started
        self.assertEqual([result.text for result in results], ["ok", "ok", "ok"])
        self.assertLess(elapsed, 0.12)

    def test_unseen_targets_keep_configured_order(self):
        first = ProviderTarget("first", "https://first.example/v1", "FIRST_KEY", "auto/fast")
        second = ProviderTarget("second", "https://second.example/v1", "SECOND_KEY", "auto/fast")
        self.assertEqual(tuple(t.name for t in CloudModelRouter._ordered_targets((first, second))), ("first", "second"))

    def test_warmed_fast_target_is_selected_first(self):
        slow = ProviderTarget("slow", "https://slow.example/v1", "SLOW_KEY", "auto/fast")
        fast = ProviderTarget("fast", "https://fast.example/v1", "FAST_KEY", "auto/fast")
        CloudModelRouter._record_success(slow, 500)
        CloudModelRouter._record_success(fast, 50)
        self.assertEqual(tuple(t.name for t in CloudModelRouter._ordered_targets((slow, fast))), ("fast", "slow"))


if __name__ == "__main__":
    unittest.main()
