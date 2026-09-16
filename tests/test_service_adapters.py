import json
import unittest

from quality_of_life.account_access import AccountAccessRegistry, AccountGrant, AccountProvider, AccountRisk, AccountScope
from quality_of_life.account_integrations import AccountIdentity, ServiceProvider, TokenBroker
from quality_of_life.service_adapters import GoogleAdapter, MicrosoftAdapter, YouTubeAdapter


class FakeBroker:
    def __init__(self, token="test-token"):
        self.token = token
        self.requested = []

    def get_access_token(self, identity, required_scope):
        self.requested.append((identity.account_id, required_scope))
        return self.token


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.data).encode("utf-8")


class ServiceAdapterTests(unittest.TestCase):
    def test_google_read_uses_grant_and_never_returns_token(self):
        seen = {}

        def opener(request, timeout):
            seen["url"] = request.full_url
            seen["auth"] = request.headers["Authorization"]
            seen["timeout"] = timeout
            return FakeResponse({"emailAddress": "user@example.com"})

        broker = FakeBroker("secret-token")
        access = AccountAccessRegistry([
            AccountGrant(AccountProvider.GOOGLE, "g1", (AccountScope("gmail.metadata", "Gmail metadata"),))
        ])
        identity = AccountIdentity(ServiceProvider.GOOGLE, "g1", "Personal Google")
        result = GoogleAdapter(broker, access, opener).execute("google.gmail.profile", identity)
        self.assertTrue(result.ok)
        self.assertNotIn("secret-token", repr(result.data))
        self.assertEqual(seen["auth"], "Bearer secret-token")
        self.assertEqual(broker.requested, [("g1", "gmail.metadata")])
        self.assertEqual(seen["timeout"], 20)

    def test_microsoft_operation_requires_matching_provider(self):
        broker = FakeBroker()
        access = AccountAccessRegistry([
            AccountGrant(AccountProvider.MICROSOFT, "m1", (AccountScope("User.Read", "Read profile"),))
        ])
        identity = AccountIdentity(ServiceProvider.GOOGLE, "m1", "Wrong provider")
        result = MicrosoftAdapter(broker, access, lambda *args, **kwargs: None).execute("microsoft.me", identity)
        self.assertFalse(result.ok)
        self.assertIn("does not match", result.error)
        self.assertEqual(broker.requested, [])

    def test_youtube_read_uses_youtube_grant(self):
        seen = {}

        def opener(request, timeout):
            seen["url"] = request.full_url
            return FakeResponse({"items": [{"id": "channel-1"}]})

        broker = FakeBroker()
        access = AccountAccessRegistry([
            AccountGrant(AccountProvider.YOUTUBE, "y1", (AccountScope("youtube.readonly", "Read YouTube data"),))
        ])
        identity = AccountIdentity(ServiceProvider.YOUTUBE, "y1", "YouTube")
        result = YouTubeAdapter(broker, access, opener).execute("youtube.channel", identity)
        self.assertTrue(result.ok)
        self.assertIn("mine=true", seen["url"])

    def test_unauthorized_scope_fails_before_network(self):
        network_calls = []
        access = AccountAccessRegistry([
            AccountGrant(AccountProvider.GOOGLE, "g1", (AccountScope("calendar.events.readonly", "Calendar"),))
        ])
        identity = AccountIdentity(ServiceProvider.GOOGLE, "g1", "Google")
        result = GoogleAdapter(FakeBroker(), access, lambda *args, **kwargs: network_calls.append(1)).execute(
            "google.gmail.profile", identity
        )
        self.assertFalse(result.ok)
        self.assertIn("scope not authorized", result.error)
        self.assertEqual(network_calls, [])


if __name__ == "__main__":
    unittest.main()
