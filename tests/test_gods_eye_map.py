from quality_of_life.gods_eye import GeoPoint, LocationSnapshot, Place
from quality_of_life.gods_eye_map import GodsEyeMap


def test_search_view_is_pure_and_serializable():
    places = (
        Place("A", GeoPoint(1, 2), "a", "fake"),
        Place("B", GeoPoint(3, 4), "b", "fake"),
    )
    view = GodsEyeMap.build_search_view(places, selected=places[1])
    payload = view.as_dict()
    assert payload["surface"] == "gods-eye"
    assert payload["center"] == {"latitude": 3, "longitude": 4}
    assert len(payload["markers"]) == 2


def test_location_view_returns_none_when_location_is_not_permitted():
    snapshot = LocationSnapshot(None, None, False, "denied")
    assert GodsEyeMap.build_location_view(snapshot) is None


def test_route_view_contains_origin_and_destination_markers():
    origin = GeoPoint(1, 2)
    destination = Place("B", GeoPoint(3, 4), "b", "fake")
    view = GodsEyeMap.build_route_view(origin, destination)
    assert view.route is not None
    assert len(view.markers) == 1
    assert view.center == origin
