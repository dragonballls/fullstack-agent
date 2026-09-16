import json
import tempfile
import unittest
from pathlib import Path

from quality_of_life.account_access import AccountAccessRegistry, AccountGrant, AccountProvider, AccountRisk, AccountScope
from quality_of_life.account_integrations import AccountIdentity, ServiceProvider
from quality_of_life.service_adapters import GoogleAdapter, MicrosoftAdapter, YouTubeAdapter


class FakeBroker:
    def __init__(self, token="test-token"):
        self.token = token
        self.requested = []

    def get_access_token(self, identity, required_scope):
        self.requested.append((identity.account_id, required_scope))
        return self.token


class FakeHeaders(dict):
    pass


class FakeResponse:
    def __init__(self, data=None, headers=None):
        self.data = data
        self.headers = FakeHeaders(headers or {})

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.data if self.data is not None else {}).encode("utf-8")


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

    def test_google_send_requires_confirmation_and_hides_message_token(self):
        seen = {}
        access = AccountAccessRegistry([
            AccountGrant(AccountProvider.GOOGLE, "g1", (AccountScope("gmail.send", "Send Gmail", AccountRisk.WRITE),))
        ])
        identity = AccountIdentity(ServiceProvider.GOOGLE, "g1", "Google")

        def opener(request, timeout):
            seen["body"] = request.data.decode("utf-8")
            return FakeResponse({"id": "message-1"})

        broker = FakeBroker("secret-token")
        blocked = GoogleAdapter(broker, access, opener).execute(
            "google.gmail.send", identity, {"to": "person@example.com", "subject": "Hello", "body": "Body"}
        )
        self.assertFalse(blocked.ok)
        self.assertIn("confirmation required", blocked.error)
        self.assertEqual(seen, {})

        result = GoogleAdapter(broker, access, opener).execute(
            "google.gmail.send", identity, {"to": "person@example.com", "subject": "Hello", "body": "Body"}, confirmed=True
        )
        self.assertTrue(result.ok)
        self.assertNotIn("secret-token", repr(result.data))
        self.assertIn("raw", seen["body"])

    def test_microsoft_send_uses_mail_send_scope(self):
        seen = {}
        access = AccountAccessRegistry([
            AccountGrant(AccountProvider.MICROSOFT, "m1", (AccountScope("Mail.Send", "Send mail", AccountRisk.WRITE),))
        ])
        identity = AccountIdentity(ServiceProvider.MICROSOFT, "m1", "Microsoft")

        def opener(request, timeout):
            seen["method"] = request.method
            seen["url"] = request.full_url
            seen["body"] = request.data.decode("utf-8")
            return FakeResponse(None)

        result = MicrosoftAdapter(FakeBroker(), access, opener).execute(
            "microsoft.mail.send", identity,
            {"to": "person@example.com", "subject": "Hello", "body": "Body"},
            confirmed=True,
        )
        self.assertTrue(result.ok)
        self.assertEqual(seen["method"], "POST")
        self.assertIn("sendMail", seen["url"])
        self.assertIn("person@example.com", seen["body"])

    def test_youtube_upload_uses_resumable_session_and_never_returns_token(self):
        seen = []
        access = AccountAccessRegistry([
            AccountGrant(AccountProvider.YOUTUBE, "y1", (AccountScope("youtube.upload", "Upload videos", AccountRisk.WRITE),))
        ])
        identity = AccountIdentity(ServiceProvider.YOUTUBE, "y1", "YouTube")

        def opener(request, timeout):
            seen.append((request.method, request.full_url, request.data, dict(request.headers), timeout))
            if request.method == "POST":
                return FakeResponse(None, {"Location": "https://upload.example/session"})
            return FakeResponse({"id": "video-1"})

        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir) / "clip.mp4"
            video.write_bytes(b"video-data")
            result = YouTubeAdapter(FakeBroker("secret-token"), access, opener).execute(
                "youtube.video.upload",
                identity,
                {"file_path": str(video), "title": "Test", "privacy": "private"},
                confirmed=True,
            )
        self.assertTrue(result.ok)
        self.assertEqual([item[0] for item in seen], ["POST", "PUT"])
        self.assertEqual(seen[1][2], b"video-data")
        self.assertNotIn("secret-token", repr(result.data))


if __name__ == "__main__":
    unittest.main()
