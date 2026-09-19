import unittest
from types import SimpleNamespace

from quality_of_life.gods_eye import GeoPoint, LocationSnapshot
from quality_of_life.gods_eye_globe import globe_payload


class GlobeTests(unittest.TestCase):
    def test_authorized_current_and_saved(self):
        class Runtime:
            def dispatch(self, capability, operation):
                if operation == "locations.current":
                    return LocationSnapshot(GeoPoint(10, 20), 25, True, "test")
                if operation == "locations.list":
                    return [SimpleNamespace(as_dict=lambda: {
                        "name": "Home",
                        "point": {"latitude": 30, "longitude": 40},
                        "source": "test",
                    })]
                raise AssertionError(operation)
        payload = globe_payload(Runtime())
        self.assertTrue(payload["authorized_current"])
        self.assertEqual(len(payload["locators"]), 2)

    def test_provider_locations_are_added(self):
        class Provider:
            def status(self):
                return {"available": True, "authorized": True, "live": True, "source": "phone"}
            def locations(self):
                return [{"label": "Phone", "point": {"latitude": 1, "longitude": 2}, "authorized": True, "source": "phone"}]

        class Eye:
            def provider_locations(self, kind):
                return [{"label": "Phone", "point": {"latitude": 1, "longitude": 2}, "authorized": True, "source": "phone"}] if kind == "phone" else []

        class Runtime:
            def __init__(self):
                self.eye = Eye()
            def dispatch(self, capability, operation):
                if operation == "locations.current":
                    return LocationSnapshot(None, None, False, "test")
                if operation == "locations.list":
                    return []
                raise AssertionError(operation)
            def _tool(self, name):
                if name == "gods_eye":
                    return self.eye
                raise AssertionError(name)

        payload = globe_payload(Runtime())
        self.assertEqual(len(payload["locators"]), 1)
        self.assertEqual(payload["locators"][0]["kind"], "phone")


    def test_sensor_state_explains_when_current_feed_is_unavailable(self):
        class Runtime:
            def dispatch(self, capability, operation):
                if operation == "locations.current":
                    return LocationSnapshot(None, None, False, "windows-location")
                if operation == "locations.list":
                    return []
                raise AssertionError(operation)

        payload = globe_payload(Runtime())

        self.assertEqual(payload["sensor_state"], "feeds-unavailable-or-unauthorized")
        self.assertEqual(payload["current_source"], "windows-location")
        self.assertIsNone(payload["current_accuracy_m"])

    def test_sensor_state_reports_live_authorized_provider(self):
        class Registry:
            def status(self, kind):
                return SimpleNamespace(as_dict=lambda: {
                    "kind": kind,
                    "available": kind == "phone",
                    "authorized": kind == "phone",
                    "live": kind == "phone",
                    "source": "phone",
                    "detail": "connected",
                })

        class Eye:
            provider_registry = Registry()
            def provider_locations(self, kind):
                return []

        class Runtime:
            def dispatch(self, capability, operation):
                if operation == "locations.current":
                    return LocationSnapshot(None, None, False, "")
                if operation == "locations.list":
                    return []
                raise AssertionError(operation)
            def _tool(self, name):
                if name == "gods_eye":
                    return Eye()
                raise AssertionError(name)

        payload = globe_payload(Runtime())

        self.assertEqual(payload["sensor_state"], "authorized-feeds-live")
        self.assertEqual(payload["provider_status"][1]["kind"], "phone")

    def test_unpermitted_current_is_hidden(self):
        class Runtime:
            def dispatch(self, capability, operation):
                if operation == "locations.current":
                    return LocationSnapshot(GeoPoint(10, 20), None, False, "test")
                if operation == "locations.list":
                    return []
                raise AssertionError(operation)
        self.assertEqual(globe_payload(Runtime())["locators"], [])


if __name__ == "__main__":
    unittest.main()
