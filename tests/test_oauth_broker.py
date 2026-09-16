import json
import os
import unittest
from urllib.parse import parse_qs, urlparse

from quality_of_life.account_integrations import AccountIdentity, ServiceProvider, OAuthConfigurationError
from quality_of_life.oauth_broker import (
    KeyringTokenStore,
    OAuthBroker,
    OAuthStateError,
    OAuthTokenSet,
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

    def test_begin_rejects_non_loopback_redirect(self):
        os.environ["JARVIS_GOOGLE_CLIENT_ID"] = "client-id-123"
        broker = OAuthBroker(dict((c.provider, c) for c in build_default_oauth_configs()), token_store=self.store)
        for redirect_uri in (
            "http://127.0.0.1:48123@evil.example/oauth/callback",
            "http://localhost:48123/oauth/callback",
            "https://127.0.0.1:48123/oauth/callback",
            "http://127.0.0.1:48123/oauth/callback#fragment",
        ):
            with self.subTest(redirect_uri=redirect_uri):
                with self.assertRaises(OAuthConfigurationError):
                    broker.begin(ServiceProvider.GOOGLE, redirect_uri=redirect_uri)

    def test_stale_oauth_state_is_rejected(self):
        os.environ["JARVIS_GOOGLE_CLIENT_ID"] = "client-id-123"
        now = [1000.0]
        broker = OAuthBroker(
            dict((c.provider, c) for c in build_default_oauth_configs()),
            token_store=self.store,
            time_fn=lambda: now[0],
            pending_ttl_seconds=300.0,
        )
        _, pending = broker.begin(ServiceProvider.GOOGLE, redirect_uri="http://127.0.0.1:48123/oauth/callback")
        now[0] = 1301.0
        with self.assertRaises(OAuthStateError):
            broker.exchange(pending, "authorization-code")

    def test_callback_rejects_wrong_state(self):
        with self.assertRaises(OAuthStateError):
            OAuthBroker.validate_callback("http://127.0.0.1:1234/callback?code=abc&state=wrong", "expected")

    def test_initial_token_is_stored(self):
        broker = OAuthBroker(dict((c.provider, c) for c in build_default_oauth_configs()), token_store=self.store)
        broker.save_initial(self.identity, OAuthTokenSet("access-secret", "refresh-secret", 9999999999, scope="openid https://www.googleapis.com/auth/gmail.readonly"))
        stored = self.store.load(self.identity)
        self.assertEqual(stored.access_token, "access-secret")
        self.assertEqual(stored.refresh_token, "refresh-secret")

    def test_scope_alias_accepts_canonical_provider_scope(self):
        self.assertTrue(scope_matches("gmail.metadata", "https://www.googleapis.com/auth/gmail.readonly"))
        self.assertTrue(scope_matches("User.Read", "User.Read Mail.Read"))
        self.assertFalse(scope_matches("youtube.readonly", "openid email"))

    def test_secure_broker_refreshes_expired_token_and_persists_result(self):
        self.store.save(
            self.identity,
            OAuthTokenSet("old-access", "refresh-secret", 0.0, scope="https://www.googleapis.com/auth/gmail.readonly"),
        )
        refreshed = OAuthTokenSet("new-access", "refresh-secret-2", 9999999999, scope="https://www.googleapis.com/auth/gmail.readonly")

        class FakeOAuth:
            def __init__(self, store):
                self.store = store
            def refresh(self, identity):
                self.store.save(identity, refreshed)
                return refreshed

        token = SecureTokenBroker(FakeOAuth(self.store), self.store).get_access_token(self.identity, "gmail.metadata")
        self.assertEqual(token, "new-access")
        self.assertEqual(self.store.load(self.identity).refresh_token, "refresh-secret-2")

    def tearDown(self):
        os.environ.pop("JARVIS_GOOGLE_CLIENT_ID", None)


if __name__ == "__main__":
    unittest.main()
