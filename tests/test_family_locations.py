from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from quality_of_life.family_locations import FamilyLocation, FamilyLocationService, Life360LocationAdapter


class FamilyLocationTests(unittest.TestCase):
    def test_normalizes_authorized_provider_payload(self):
        adapter = Life360LocationAdapter()
        locations = adapter.normalize({
            "members": [{
                "id": "member-1",
                "name": "Alex",
                "latitude": 34.1,
                "longitude": -117.9,
                "accuracy_m": 12,
                "updated_at": "2026-09-16T20:00:00+00:00",
                "sharing": "on",
            }]
        })
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].member_id, "member-1")
        self.assertEqual(locations[0].name, "Alex")
        self.assertEqual(locations[0].latitude, 34.1)
        self.assertFalse(locations[0].stale)

    def test_rejects_malformed_coordinates(self):
        with self.assertRaises(ValueError):
            Life360LocationAdapter().normalize({"members": [{"id": "x", "name": "X"}]})

    def test_sharing_paused_is_not_reported_as_live(self):
        locations = Life360LocationAdapter().normalize({
            "members": [{
                "id": "member-1",
                "name": "Alex",
                "latitude": 34.1,
                "longitude": -117.9,
                "updated_at": "2026-09-16T20:00:00+00:00",
                "sharing": "paused",
            }]
        })
        self.assertEqual(locations[0].sharing_state, "paused")
        self.assertFalse(locations[0].available)

    def test_stale_location_is_explicitly_marked(self):
        observed = datetime.now(timezone.utc) - timedelta(hours=2)
        location = FamilyLocation(
            member_id="x", name="Alex", latitude=34.1, longitude=-117.9,
            accuracy_m=None, source="fixture", observed_at=observed,
            sharing_state="on", stale_after_seconds=60,
        )
        self.assertTrue(location.stale)
        self.assertTrue(location.available)

    def test_follow_ignores_older_update(self):
        service = FamilyLocationService()
        first = FamilyLocation("x", "Alex", 34.1, -117.9, None, "fixture", datetime(2026, 1, 2, tzinfo=timezone.utc), "on")
        second = FamilyLocation("x", "Alex", 35.1, -118.9, None, "fixture", datetime(2026, 1, 1, tzinfo=timezone.utc), "on")
        service.apply([first])
        service.follow("x")
        self.assertFalse(service.apply([second]))
        self.assertEqual(service.get("x").latitude, 34.1)

    def test_follow_moves_on_newer_update(self):
        service = FamilyLocationService()
        first = FamilyLocation("x", "Alex", 34.1, -117.9, None, "fixture", datetime(2026, 1, 1, tzinfo=timezone.utc), "on")
        second = FamilyLocation("x", "Alex", 35.1, -118.9, None, "fixture", datetime(2026, 1, 2, tzinfo=timezone.utc), "on")
        service.apply([first])
        service.follow("x")
        self.assertFalse(service.following() is None)
        self.assertTrue(service.apply([second]))
        self.assertEqual(service.following().member_id, "x")
        self.assertEqual(service.followed_location().latitude, 35.1)

    def test_ambiguous_name_does_not_guess(self):
        service = FamilyLocationService()
        service.apply([
            FamilyLocation("a", "Alex", 34.1, -117.9, None, "fixture", datetime.now(timezone.utc), "on"),
            FamilyLocation("b", "Alex", 35.1, -118.9, None, "fixture", datetime.now(timezone.utc), "on"),
        ])
        with self.assertRaises(ValueError):
            service.get("Alex")


if __name__ == "__main__":
    unittest.main()
