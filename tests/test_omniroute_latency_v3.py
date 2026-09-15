import unittest

from quality_of_life.router import CloudModelRouter


class OmniRouteLatencyV3Tests(unittest.TestCase):
    def test_router_has_latency_metric_api(self):
        self.assertTrue(hasattr(CloudModelRouter, "provider_latency_ms"))


if __name__ == "__main__":
    unittest.main()
