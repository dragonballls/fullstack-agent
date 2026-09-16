import os
import unittest

from quality_of_life.account_integrations import AccountIdentity, ServiceProvider, OAuthConfigurationError
from quality_of_life.account_manager import AccountServiceManager


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


if __name__ == "__main__":
    unittest.main()
