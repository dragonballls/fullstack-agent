import os
import unittest
from unittest.mock import patch

from quality_of_life.orchestration import RequestProfile
from quality_of_life.router import CloudModelRouter, ProviderTarget


class RouterLatencyTests(unittest.TestCase):
    def test_provider_latency_is_scoped_to_named_target(self) -> None:
        first = ProviderTarget("fast", "https://fast.example.test/v1", "FAST_KEY", "shared-model")
        second = ProviderTarget("slow", "https://slow.example.test/v1", "SLOW_KEY", "shared-model")
        key_first = CloudModelRouter._health_key(first)
        key_second = CloudModelRouter._health_key(second)
        with patch.dict(os.environ, {"JARVIS_OMNIROUTE_SMART_MODEL": "shared-model"}):
            with CloudModelRouter._health_lock:
                old_latency = dict(CloudModelRouter._latency_ewma_ms)
                old_samples = dict(CloudModelRouter._latency_samples)
                CloudModelRouter._latency_ewma_ms.clear()
                CloudModelRouter._latency_samples.clear()
                CloudModelRouter._latency_ewma_ms[key_first] = 100.0
                CloudModelRouter._latency_ewma_ms[key_second] = 900.0
                CloudModelRouter._latency_samples[key_first] = 1
                CloudModelRouter._latency_samples[key_second] = 1
            try:
                self.assertEqual(CloudModelRouter.provider_latency_ms("slow", RequestProfile.SMART), 900)
                self.assertEqual(CloudModelRouter.provider_latency_ms("fast", RequestProfile.SMART), 100)
            finally:
                with CloudModelRouter._health_lock:
                    CloudModelRouter._latency_ewma_ms.clear()
                    CloudModelRouter._latency_ewma_ms.update(old_latency)
                    CloudModelRouter._latency_samples.clear()
                    CloudModelRouter._latency_samples.update(old_samples)


if __name__ == "__main__":
    unittest.main()
