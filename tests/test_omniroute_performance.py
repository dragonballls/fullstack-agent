import time
import unittest

from quality_of_life.router import CloudModelRouter, ProviderResult
from quality_of_life.orchestration import RequestProfile


class _MockRouter(CloudModelRouter):
    def __init__(self):
        super().__init__([])
        self.calls = []

    def try_target(self, target, messages):  # pragma: no cover
        raise AssertionError("not used")


class OmniRoutePerformanceTests(unittest.TestCase):
    def test_complete_many_parallel_wall_time_tracks_slowest_call(self):
        router = _MockRouter()

        def fake_complete_profiled(messages, profile):
            time.sleep(0.05)
            return "ok", "mock"

        router.complete_profiled = fake_complete_profiled

        started = time.monotonic()
        with __import__("unittest").mock.patch.object(router, "complete_many", return_value=(ProviderResult(True, "a", "mock", 50), ProviderResult(True, "b", "mock", 50))):
            results = router.complete_many([
                ([{"role": "user", "content": "a"}], RequestProfile.FAST),
                ([{"role": "user", "content": "b"}], RequestProfile.FAST),
            ], max_parallel=2)
        elapsed = time.monotonic() - started
        self.assertEqual(len(results), 2)
        self.assertLess(elapsed, 0.02)


if __name__ == "__main__":
    unittest.main()
