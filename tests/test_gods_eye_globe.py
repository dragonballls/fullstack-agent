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
