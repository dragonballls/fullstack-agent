import os
import unittest

from quality_of_life.account_integrations import (
    AccountIdentity,
    AccountSelectionError,
    AccountSelector,
    AuthorizationState,
    OAuthAuthorizer,
    OAuthConfigurationError,
    DEFAULT_OAUTH_CONFIGS,
    ServiceProvider,
    UnconfiguredTokenBroker,
)


class AccountIntegrationTests(unittest.TestCase):
    def test_multiple_accounts_are_selectable_without_collision(self):
        accounts = (
            AccountIdentity(ServiceProvider.GOOGLE, "g1", "Personal Google"),
            AccountIdentity(ServiceProvider.GOOGLE, "g2", "Work Google"),
        )
        selector = AccountSelector(accounts)
        self.assertEqual(selector.select(ServiceProvider.GOOGLE, label="Work Google").account_id, "g2")

    def test_ambiguous_provider_selection_is_rejected(self):
        accounts = (
            AccountIdentity(ServiceProvider.MICROSOFT, "m1", "Personal Microsoft"),
            AccountIdentity(ServiceProvider.MICROSOFT, "m2", "Other Microsoft"),
        )
        with self.assertRaisesRegex(AccountSelectionError, "choose one explicitly"):
            AccountSelector(accounts).select(ServiceProvider.MICROSOFT)

    def test_disconnected_account_is_not_selectable(self):
        account = AccountIdentity(ServiceProvider.GOOGLE, "g1", "Google", AuthorizationState.NEEDS_REAUTH)
        with self.assertRaisesRegex(AccountSelectionError, "no connected"):
            AccountSelector((account,)).select(ServiceProvider.GOOGLE)

    def test_oauth_request_never_contains_client_secret(self):
        os.environ["JARVIS_GOOGLE_CLIENT_ID"] = "test-client-id"
        try:
            url = OAuthAuthorizer(DEFAULT_OAUTH_CONFIGS).authorization_request(
                ServiceProvider.GOOGLE, state="state-123", redirect_uri="http://127.0.0.1/callback"
            )
        finally:
            os.environ.pop("JARVIS_GOOGLE_CLIENT_ID", None)
        self.assertIn("test-client-id", url)
        self.assertNotIn("client_secret", url)
        self.assertNotIn("secret", url.lower())

    def test_oauth_configuration_fails_closed_when_client_id_missing(self):
        with self.assertRaisesRegex(OAuthConfigurationError, "JARVIS_GOOGLE_CLIENT_ID"):
            OAuthAuthorizer(DEFAULT_OAUTH_CONFIGS).authorization_request(
                ServiceProvider.GOOGLE, state="state-123", redirect_uri="http://127.0.0.1/callback"
            )

    def test_unconfigured_token_broker_fails_closed(self):
        identity = AccountIdentity(ServiceProvider.GITHUB, "gh1", "GitHub")
        with self.assertRaisesRegex(OAuthConfigurationError, "no credential broker"):
            UnconfiguredTokenBroker().get_access_token(identity, "repo.read")


if __name__ == "__main__":
    unittest.main()
