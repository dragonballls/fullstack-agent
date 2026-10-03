import unittest

from quality_of_life.gods_eye import GeoPoint, LocationSnapshot, Place
from quality_of_life.gods_eye_map import GodsEyeMap


class GodsEyeMapTests(unittest.TestCase):
    def test_family_location_view_converts_authorized_provider_records_to_markers(self):
        locations = [
            {
                "id": "device_tracker.parent",
                "name": "Parent",
                "point": {"latitude": 34.1, "longitude": -117.7},
                "provider": "life360",
            },
            {
                "id": "device_tracker.sibling",
                "name": "Sibling",
                "point": {"latitude": 34.2, "longitude": -117.8},
                "provider": "life360",
            },
        ]
        view = GodsEyeMap.build_family_location_view(locations, center=GeoPoint(34.15, -117.75))
        self.assertIsNotNone(view)
        assert view is not None
        self.assertEqual(view.center, GeoPoint(34.15, -117.75))
        self.assertEqual([marker.name for marker in view.markers], ["Parent", "Sibling"])
        self.assertEqual([marker.provider for marker in view.markers], ["life360", "life360"])

    def test_family_location_view_is_none_without_valid_records(self):
        self.assertIsNone(GodsEyeMap.build_family_location_view([{"name": "bad", "point": {"latitude": "x", "longitude": 1}}]))

    def test_search_view_is_pure_and_serializable(self):
        places = (Place("A", GeoPoint(1, 2), "a", "fake"), Place("B", GeoPoint(3, 4), "b", "fake"))
        view = GodsEyeMap.build_search_view(places, selected=places[1])
        payload = view.as_dict()
        self.assertEqual(payload["surface"], "gods-eye")
        self.assertEqual(payload["center"], {"latitude": 3, "longitude": 4})
        self.assertEqual(len(payload["markers"]), 2)

    def test_location_view_returns_none_when_location_is_not_permitted(self):
        self.assertIsNone(GodsEyeMap.build_location_view(LocationSnapshot(None, None, False, "denied")))

    def test_route_view_contains_origin_and_destination_markers(self):
        origin = GeoPoint(1, 2)
        destination = Place("B", GeoPoint(3, 4), "b", "fake")
        view = GodsEyeMap.build_route_view(origin, destination)
        self.assertIsNotNone(view.route)
        self.assertEqual(len(view.markers), 1)
        self.assertEqual(view.center, origin)
