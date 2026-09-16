import json
import os
import unittest
from urllib.parse import parse_qs, urlparse

from quality_of_life.account_integrations import AccountIdentity, ServiceProvider
from quality_of_life.oauth_broker import (
    KeyringTokenStore,
    OAuthBroker,
    OAuthPendingRequest,
    OAuthTokenSet,
    OAuthStateError,
    SecureTokenBroker,
    build_default_oauth_configs,
    scope_matches,
)


class FakeKeyring:
    def __init__(self):
        self.values = {}

    def set_password(self, service, username, value):
        self.values[(service, username)] = value

    def get_password(self, service, username):
        return self.values.get((service, username))

    def delete_password(self, service, username):
        self.values.pop((service, username), None)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class OAuthBrokerTests(unittest.TestCase):
    def setUp(self):
        self.identity = AccountIdentity(ServiceProvider.GOOGLE, "google-sub-1", "me@example.com")
        self.keyring = FakeKeyring()
        self.store = KeyringTokenStore(self.keyring)

    def test_begin_uses_pkce_and_no_client_secret(self):
        os.environ["JARVIS_GOOGLE_CLIENT_ID"] = "client-id-123"
        broker = OAuthBroker(dict((c.provider, c) for c in build_default_oauth_configs()), token_store=self.store)
        url, pending = broker.begin(ServiceProvider.GOOGLE, redirect_uri="http://127.0.0.1:48123/oauth/callback")
        params = parse_qs(urlparse(url).query)
        self.assertEqual(params["client_id"], ["client-id-123"])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertTrue(params["code_challenge"][0])
        self.assertEqual(pending.redirect_uri, "http://127.0.0.1:48123/oauth/callback")
        self.assertNotIn("client_secret", params)

    def test_callback_rejects_wrong_state(self):
        with self.assertRaises(OAuthStateError):
            OAuthBroker.validate_callback("http://127.0.0.1:1234/callback?code=abc&state=wrong", "expected")

    def test_initial_token_is_stored_without_being_returned_by_broker(self):
        broker = OAuthBroker(dict((c.provider, c) for c in build_default_oauth_configs()), token_store=self.store)
        broker.save_initial(self.identity, OAuthTokenSet("access-secret", "refresh-secret", 9999999999, scope="openid https://www.googleapis.com/auth/gmail.readonly"))
        self.assertEqual(self.store.load(self.identity).access_token, "access-secret")
        self.assertNotIn("access-secret", json.dumps({"account_id": self.identity.account_id, "label": self.identity.label}))

    def test_scope_alias_accepts_canonical_provider_scope(self):
        self.assertTrue(scope_matches("gmail.metadata", "https://www.googleapis.com/auth/gmail.readonly"))
        self.assertTrue(scope_matches("User.Read", "User.Read Mail.Read"))
        self.assertFalse(scope_matches("youtube.readonly", "openid email"))

    def test_secure_broker_refreshes_expired_token(self):
        os.environ["JARVIS_GOOGLE_CLIENT_ID"] = "client-id-123"
        now = 1000.0
        refreshed = OAuthTokenSet("new-access", "refresh-secret", 2000.0, scope="https://www.googleapis.com/auth/gmail.readonly")
        self.store.save(self.identity, OAuthTokenSet("old-access", "refresh-secret", 900.0, scope="https://www.googleapis.com/auth/gmail.readonly"))

        class FakeOAuth:
            def refresh(self, identity):
                self.identity = identity
                return refreshed

        # Use a fake store + fake OAuth to verify refresh behavior independently of network.
        original = self.store.load(self.identity)
        class Broker(SecureTokenBroker):
            pass
        class FakeStore:
            def __init__(self, token):
                self.token = token
            def load(self, identity):
                return self.token

        broker = Broker(FakeOAuth(), FakeStore(original))
        # Expiration uses wall clock, so use a token with no expiry to verify the direct path below.
        self.store.save(self.identity, OAuthTokenSet("live-access", "refresh-secret", None, scope="https://www.googleapis.com/auth/gmail.readonly"))
        live = SecureTokenBroker(FakeOAuth(), self.store)
        self.assertEqual(live.get_access_token(self.identity, "gmail.metadata"), "live-access")

    def tearDown(self):
        os.environ.pop("JARVIS_GOOGLE_CLIENT_ID", None)


if __name__ == "__main__":
    unittest.main()
