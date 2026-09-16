import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quality_of_life.account_access import AccountAccessRegistry, AccountGrant, AccountProvider, AccountRisk, AccountScope
from quality_of_life.account_integrations import AccountIdentity, ServiceProvider, OAuthConfigurationError
from quality_of_life.account_manager import AccountServiceManager
from quality_of_life.account_store import AccountStore
from quality_of_life.oauth_broker import OAuthTokenSet


class FakeWriteBroker:
    def __init__(self, token="token"):
        self.token = token
        self.requested = []

    def get_access_token(self, identity, required_scope):
        self.requested.append((identity.account_id, required_scope))
        return self.token


class FakeResponse:
    def __init__(self, data):
        self.data = data
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        import json
        return json.dumps(self.data).encode("utf-8")


class FakeAdapter:
    def __init__(self, broker, access):
        self.broker = broker
        self.access = access

    def execute(self, operation, identity, payload=None, *, confirmed=False):
        token = self.broker.get_access_token(identity, "gmail.send")
        self.access.require(AccountProvider.GOOGLE, identity.account_id, "gmail.send", confirmed=confirmed)
        return type("Result", (), {"ok": bool(token), "error": None, "data": {"id": "message-1"}})()


class AccountRuntimeTests(unittest.TestCase):
    def test_multiple_accounts_remain_distinct(self):
        manager = AccountServiceManager(
            identities=(
                AccountIdentity(ServiceProvider.GOOGLE, "g1", "Personal Google"),
                AccountIdentity(ServiceProvider.GOOGLE, "g2", "Work Google"),
            )
        )
        self.assertEqual(manager.select_account(ServiceProvider.GOOGLE, label="Work Google").account_id, "g2")
        self.assertEqual({account.account_id for account in manager.list_accounts(ServiceProvider.GOOGLE)}, {"g1", "g2"})

    def test_oauth_connection_url_requires_client_configuration(self):
        os.environ.pop("JARVIS_GOOGLE_CLIENT_ID", None)
        with self.assertRaises(OAuthConfigurationError):
            AccountServiceManager().authorization_url(
                ServiceProvider.GOOGLE,
                state="state",
                redirect_uri="http://127.0.0.1/callback",
            )

    def test_oauth_connection_url_contains_no_secret(self):
        os.environ["JARVIS_MICROSOFT_CLIENT_ID"] = "client-id"
        try:
            url = AccountServiceManager().authorization_url(
                ServiceProvider.MICROSOFT,
                state="state",
                redirect_uri="http://127.0.0.1/callback",
            )
        finally:
            os.environ.pop("JARVIS_MICROSOFT_CLIENT_ID", None)
        self.assertIn("client-id", url)
        self.assertNotIn("client_secret", url)

    def test_successful_reconnect_reenables_previous_disabled_grant(self):
        identity = AccountIdentity(ServiceProvider.GOOGLE, "g1", "Personal Google")
        grant = AccountGrant(
            AccountProvider.GOOGLE,
            identity.account_id,
            (AccountScope("gmail.metadata", "Read Gmail", AccountRisk.READ),),
            enabled=False,
        )
        access = AccountAccessRegistry((grant,))
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AccountServiceManager(
                identities=(identity,),
                account_access=access,
                account_store=AccountStore(Path(temp_dir) / "accounts.json"),
            )
            fake_token = OAuthTokenSet("access", "refresh", 9999999999, scope="openid email profile https://www.googleapis.com/auth/gmail.readonly")
            with patch.object(manager, "_secure_oauth", return_value=object()), patch(
                "quality_of_life.account_manager.connect_in_browser",
                return_value=(identity, fake_token),
            ):
                manager.connect_account(ServiceProvider.GOOGLE)
            self.assertTrue(manager.account_access.get(AccountProvider.GOOGLE, identity.account_id).enabled)
            self.assertTrue(manager.account_access.get(AccountProvider.GOOGLE, identity.account_id).allows("gmail.metadata"))

    def test_confirmed_write_adds_only_the_requested_local_grant(self):
        identity = AccountIdentity(ServiceProvider.GOOGLE, "g1", "Google")
        access = AccountAccessRegistry([AccountGrant(AccountProvider.GOOGLE, "g1", ())])
        broker = FakeWriteBroker()
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AccountServiceManager(
                identities=(identity,),
                account_access=access,
                token_broker=broker,
                account_store=AccountStore(Path(temp_dir) / "accounts.json"),
            )
            with patch("quality_of_life.account_manager.GoogleAdapter", FakeAdapter):
                result = manager.service_action(
                    "google.gmail.send",
                    provider=ServiceProvider.GOOGLE,
                    account_id="g1",
                    payload={"to": "person@example.com", "subject": "Hello", "body": "Body"},
                    confirmed=True,
                )
            self.assertTrue(result.ok)
            self.assertEqual(broker.requested, [("g1", "gmail.send")])
            grant = manager.account_access.get(AccountProvider.GOOGLE, "g1")
            self.assertTrue(grant.allows("gmail.send"))
            self.assertFalse(grant.allows("drive.readonly"))


if __name__ == "__main__":
    unittest.main()
