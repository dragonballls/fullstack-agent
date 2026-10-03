import unittest

from quality_of_life.life360 import Life360HomeAssistantProvider


class Life360HomeAssistantProviderTests(unittest.TestCase):
    def test_disabled_provider_never_calls_home_assistant(self):
        calls = []
        provider = Life360HomeAssistantProvider(
            enabled=False,
            token="secret",
            fetch_json=lambda url, token: calls.append((url, token)),
        )
        self.assertFalse(provider.status()["available"])
        self.assertEqual(provider.locations(), [])
        self.assertEqual(calls, [])

    def test_status_and_locations_use_bearer_token_without_exposing_it(self):
        calls = []
        payloads = {
            "http://127.0.0.1:8123/api/": {"message": "API running."},
            "http://127.0.0.1:8123/api/states": [
                {
                    "entity_id": "device_tracker.parent",
                    "state": "home",
                    "attributes": {
                        "friendly_name": "Parent",
                        "latitude": "34.1",
                        "longitude": "-117.7",
                        "gps_accuracy": 12,
                        "battery_level": 88,
                        "attribution": "Data provided by life360.com",
                        "address": "Home",
                        "last_seen": "2026-10-02T18:00:00+00:00",
                    },
                },
                {
                    "entity_id": "sensor.not_life360",
                    "state": "on",
                    "attributes": {},
                },
            ],
        }

        def fetch(url, token):
            calls.append((url, token))
            return payloads[url]

        provider = Life360HomeAssistantProvider(
            enabled=True,
            token="test-token",
            base_url="http://127.0.0.1:8123",
            fetch_json=fetch,
        )
        status = provider.status()
        self.assertTrue(status["available"])
        self.assertTrue(status["authorized"])
        self.assertNotIn("test-token", status["detail"])

        locations = provider.locations()
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0]["name"], "Parent")
        self.assertEqual(locations[0]["point"], {"latitude": 34.1, "longitude": -117.7})
        self.assertEqual(locations[0]["battery_level"], 88)
        self.assertEqual(locations[0]["accuracy_m"], 12)
        self.assertEqual(calls, [
            ("http://127.0.0.1:8123/api/", "test-token"),
            ("http://127.0.0.1:8123/api/", "test-token"),
            ("http://127.0.0.1:8123/api/states", "test-token"),
        ])

    def test_explicit_entity_allowlist_accepts_life360_data_without_attribution(self):
        payloads = {
            "http://127.0.0.1:8123/api/": {"message": "API running."},
            "http://127.0.0.1:8123/api/states": [
                {
                    "entity_id": "device_tracker.family_member",
                    "state": "not_home",
                    "attributes": {
                        "friendly_name": "Family member",
                        "latitude": 34,
                        "longitude": -118,
                    },
                }
            ],
        }
        provider = Life360HomeAssistantProvider(
            enabled=True,
            token="x",
            entity_ids=("device_tracker.family_member",),
            fetch_json=lambda url, _token: payloads[url],
        )
        self.assertEqual(provider.locations()[0]["name"], "Family member")

    def test_default_provider_ignores_non_life360_device_trackers(self):
        payloads = {
            "http://127.0.0.1:8123/api/": {"message": "API running."},
            "http://127.0.0.1:8123/api/states": [
                {
                    "entity_id": "device_tracker.phone",
                    "state": "home",
                    "attributes": {"latitude": 1, "longitude": 2, "friendly_name": "Phone"},
                }
            ],
        }
        provider = Life360HomeAssistantProvider(
            enabled=True,
            token="x",
            fetch_json=lambda url, _token: payloads[url],
        )
        self.assertEqual(provider.locations(), [])

    def test_invalid_public_host_is_rejected(self):
        provider = Life360HomeAssistantProvider(
            enabled=True,
            token="x",
            base_url="https://example.com",
            fetch_json=lambda *_: (_ for _ in ()).throw(AssertionError("network must not be called")),
        )
        status = provider.status()
        self.assertFalse(status["available"])
        self.assertIn("local/private", status["detail"])

    def test_malformed_life360_rows_are_skipped(self):
        payloads = {
            "http://127.0.0.1:8123/api/": {"message": "API running."},
            "http://127.0.0.1:8123/api/states": [
                {"entity_id": "device_tracker.bad", "attributes": {"attribution": "life360.com", "latitude": "x", "longitude": 1}},
                {"entity_id": "device_tracker.good", "attributes": {"attribution": "life360.com", "latitude": 3, "longitude": 4}},
            ],
        }
        provider = Life360HomeAssistantProvider(
            enabled=True,
            token="x",
            fetch_json=lambda url, _token: payloads[url],
        )
        locations = provider.locations()
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0]["point"], {"latitude": 3.0, "longitude": 4.0})


if __name__ == "__main__":
    unittest.main()
