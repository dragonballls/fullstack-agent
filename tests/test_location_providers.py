import unittest

from quality_of_life.location_providers import LocationProviderRegistry


class LocationProviderRegistryTests(unittest.TestCase):
    def test_snapshot_contains_independent_device_phone_family_slots(self):
        registry = LocationProviderRegistry()

        kinds = [item.kind for item in registry.snapshot()]

        self.assertEqual(kinds, ["device", "phone", "family"])

    def test_unregistered_provider_is_unavailable(self):
        registry = LocationProviderRegistry()

        state = registry.status("family")

        self.assertFalse(state.available)
        self.assertFalse(state.authorized)
        self.assertFalse(state.live)
        self.assertIn("unavailable", state.detail.casefold())

    def test_provider_state_is_normalized_without_inventing_coordinates(self):
        class Provider:
            def status(self):
                return {
                    "available": True,
                    "authorized": True,
                    "live": True,
                    "source": "authorized-phone",
                    "detail": "connected",
                    "latitude": 34.0,
                    "longitude": -117.0,
                }

        registry = LocationProviderRegistry()
        registry.register("phone", Provider())

        state = registry.status("phone")
        payload = state.as_dict()

        self.assertTrue(state.available)
        self.assertTrue(state.authorized)
        self.assertTrue(state.live)
        self.assertEqual(state.source, "authorized-phone")
        self.assertNotIn("latitude", payload)
        self.assertNotIn("longitude", payload)

    def test_provider_exception_is_sanitized(self):
        class Provider:
            def status(self):
                raise RuntimeError("token=SECRET123")

        registry = LocationProviderRegistry()
        registry.register("family", Provider())

        state = registry.status("family")

        self.assertFalse(state.available)
        self.assertFalse(state.authorized)
        self.assertFalse(state.live)
        self.assertIn("RuntimeError", state.detail)
        self.assertNotIn("SECRET123", state.detail)

    def test_live_defaults_false_even_when_provider_only_reports_available(self):
        class Provider:
            def status(self):
                return {"available": True, "authorized": True}

        registry = LocationProviderRegistry()
        registry.register("phone", Provider())

        self.assertFalse(registry.status("phone").live)

    def test_provider_detail_masks_common_secret_patterns(self):
        class Provider:
            def status(self):
                return {
                    "available": True,
                    "authorized": True,
                    "detail": "token=SECRET123 authorization=Bearer SECRET456",
                }

        registry = LocationProviderRegistry()
        registry.register("phone", Provider())

        detail = registry.status("phone").detail

        self.assertNotIn("SECRET123", detail)
        self.assertNotIn("SECRET456", detail)
        self.assertIn("[redacted]", detail)



if __name__ == "__main__":
    unittest.main()
