import unittest

from quality_of_life.gods_eye import GeoPoint, LocationSnapshot
from quality_of_life.location import NominatimGeocoder, SystemLocationProvider


class GodsEyeProviderTests(unittest.TestCase):
    def test_nominatim_normalizes_valid_records(self):
        payload = [{"display_name": "Tokyo, Japan", "lat": "35.6762", "lon": "139.6503", "type": "city", "osm_id": 1}]
        geocoder = NominatimGeocoder(fetch_json=lambda _url: payload)
        places = geocoder.search("Tokyo")
        self.assertEqual(places[0].name, "Tokyo, Japan")
        self.assertEqual(places[0].point, GeoPoint(35.6762, 139.6503))
        self.assertEqual(places[0].place_id, "1")

    def test_nominatim_skips_malformed_rows_and_transport_failures(self):
        geocoder = NominatimGeocoder(fetch_json=lambda _url: [{"display_name": "bad", "lat": "x"}, {"display_name": "ok", "lat": "1", "lon": "2"}])
        self.assertEqual(len(geocoder.search("x")), 1)
        broken = NominatimGeocoder(fetch_json=lambda _url: (_ for _ in ()).throw(OSError("offline")))
        self.assertEqual(broken.search("x"), [])

    def test_system_location_defaults_to_explicitly_unavailable(self):
        self.assertEqual(SystemLocationProvider().current(), LocationSnapshot(None, None, False, "unavailable"))

    def test_system_location_accepts_injected_location_callback(self):
        expected = LocationSnapshot(GeoPoint(34.1, -117.7), 15.0, True, "test")
        self.assertEqual(SystemLocationProvider(get_location=lambda: expected).current(), expected)
