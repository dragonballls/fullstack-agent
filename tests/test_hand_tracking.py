import unittest

from quality_of_life.hand_control import HandSample
from quality_of_life.hand_tracking import BrowserHandTrackingAdapter, sample_from_payload


class HandTrackingTests(unittest.TestCase):
    def test_payload_maps_to_normalized_sample(self):
        sample = sample_from_payload({"x": 0.2, "y": 0.4, "pinch": True, "fingers": 1, "confidence": 0.91})
        self.assertIsInstance(sample, HandSample)
        self.assertEqual((sample.x, sample.y, sample.fingers), (0.2, 0.4, 1))

    def test_payload_rejects_out_of_range_values(self):
        with self.assertRaises(ValueError):
            sample_from_payload({"x": 1.2, "y": 0.4, "pinch": False, "fingers": 1, "confidence": 1.0})
        with self.assertRaises(ValueError):
            sample_from_payload({"x": 0.2, "y": 0.4, "pinch": False, "fingers": 6, "confidence": 1.0})

    def test_adapter_reports_permission_degradation(self):
        adapter = BrowserHandTrackingAdapter()
        self.assertTrue(adapter.status().available)
        self.assertFalse(adapter.status(camera_permission=False).available)


if __name__ == "__main__":
    unittest.main()
