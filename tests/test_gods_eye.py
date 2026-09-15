import pytest

from quality_of_life.gods_eye import GeoPoint, GodsEye, LocationSnapshot, Place


class FakeGeocoder:
    def __init__(self, places):
        self.places = places
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        return list(self.places)


class FakeLocationProvider:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def current(self):
        return self.snapshot


def test_geo_point_validates_bounds():
    assert GeoPoint(34.1, -117.7).longitude == -117.7
    with pytest.raises(ValueError):
        GeoPoint(91, 0)
    with pytest.raises(ValueError):
        GeoPoint(0, 181)


def test_search_returns_structured_places_and_rejects_empty_queries():
    place = Place("Tokyo", GeoPoint(35.6762, 139.6503), "tokyo", "fake")
    geocoder = FakeGeocoder([place])
    eye = GodsEye(geocoder=geocoder, location_provider=FakeLocationProvider(LocationSnapshot(None, None, False, "none")))
    assert eye.search("Tokyo") == [place]
    assert geocoder.queries == ["Tokyo"]
    with pytest.raises(ValueError):
        eye.search("   ")


def test_locate_me_never_claims_a_location_without_permission():
    snapshot = LocationSnapshot(None, None, False, "permission-denied")
    eye = GodsEye(FakeGeocoder([]), FakeLocationProvider(snapshot))
    assert eye.locate_me() == snapshot
    context = eye.context()
    assert context["location"]["permitted"] is False
    assert context["location"]["point"] is None


def test_route_is_deterministic_and_uses_valid_coordinates():
    origin = GeoPoint(34.1, -117.7)
    destination = Place("Los Angeles", GeoPoint(34.0522, -118.2437), "la", "fake")
    eye = GodsEye(FakeGeocoder([destination]), FakeLocationProvider(LocationSnapshot(origin, 20.0, True, "fake")))
    route = eye.route(origin, destination)
    assert route["origin"] == {"latitude": 34.1, "longitude": -117.7}
    assert route["destination"] == {"latitude": 34.0522, "longitude": -118.2437}
    assert route["provider"] == "openstreetmap"
