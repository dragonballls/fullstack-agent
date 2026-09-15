import os
import unittest
from unittest.mock import patch

from quality_of_life.gods_eye import GeoPoint, LocationSnapshot
from quality_of_life.location import FallbackLocationProvider, IpLocationProvider, NominatimGeocoder, SystemLocationProvider


class GodsEyeProviderTests(unittest.TestCase):
    def test_nominatim_normalizes_valid_records(self):
        payload = [{"display_name": "Tokyo, Japan", "lat": "35.6762", "lon": "139.6503", "type": "city", "osm_id": 1}]
        places = NominatimGeocoder(fetch_json=lambda _url: payload).search("Tokyo")
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

    def test_ip_location_is_opt_in_and_marked_approximate(self):
        payload = {"latitude": 34.1, "longitude": -117.7}
        provider = IpLocationProvider(fetch_json=lambda _url: payload)
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(provider.current().permitted)
        with patch.dict(os.environ, {"JARVIS_ALLOW_IP_LOCATION": "1"}, clear=False):
            snapshot = provider.current()
        self.assertTrue(snapshot.permitted)
        self.assertEqual(snapshot.point, GeoPoint(34.1, -117.7))
        self.assertEqual(snapshot.accuracy_m, 25000.0)

    def test_fallback_prefers_explicit_system_location(self):
        primary = SystemLocationProvider(get_location=lambda: LocationSnapshot(GeoPoint(1, 2), 10, True, "system"))
        fallback = IpLocationProvider(fetch_json=lambda _url: {"latitude": 3, "longitude": 4})
        with patch.dict(os.environ, {"JARVIS_ALLOW_IP_LOCATION": "1"}, clear=False):
            self.assertEqual(FallbackLocationProvider(primary, fallback).current().point, GeoPoint(1, 2))
