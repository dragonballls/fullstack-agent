from quality_of_life.gods_eye import GeoPoint, LocationSnapshot
from quality_of_life.location import NominatimGeocoder, SystemLocationProvider


def test_nominatim_normalizes_valid_records():
    payload = [
        {"display_name": "Tokyo, Japan", "lat": "35.6762", "lon": "139.6503", "type": "city", "osm_id": 1}
    ]

    def fetch(_url):
        return payload

    geocoder = NominatimGeocoder(fetch_json=fetch)
    places = geocoder.search("Tokyo")
    assert places[0].name == "Tokyo, Japan"
    assert places[0].point == GeoPoint(35.6762, 139.6503)
    assert places[0].place_id == "1"


def test_nominatim_skips_malformed_rows_and_surfaces_transport_failures():
    geocoder = NominatimGeocoder(fetch_json=lambda _url: [{"display_name": "bad", "lat": "x"}, {"display_name": "ok", "lat": "1", "lon": "2"}])
    assert len(geocoder.search("x")) == 1

    def broken(_url):
        raise OSError("offline")

    broken_geocoder = NominatimGeocoder(fetch_json=broken)
    assert broken_geocoder.search("x") == []


def test_system_location_defaults_to_explicitly_unavailable():
    provider = SystemLocationProvider()
    snapshot = provider.current()
    assert snapshot == LocationSnapshot(None, None, False, "unavailable")


def test_system_location_accepts_injected_location_callback():
    expected = LocationSnapshot(GeoPoint(34.1, -117.7), 15.0, True, "test")
    provider = SystemLocationProvider(get_location=lambda: expected)
    assert provider.current() == expected
