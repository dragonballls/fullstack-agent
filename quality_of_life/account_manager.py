"""Unified multi-account manager for Jarvis external services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .account_access import AccountAccessRegistry, AccountGrant, AccountProvider, AccountRisk, AccountScope
from .account_integrations import (
    AccountIdentity,
    AccountSelector,
    AuthorizationState,
    DEFAULT_OAUTH_CONFIGS,
    OAuthAuthorizer,
    ServiceProvider,
    TokenBroker,
)
from .account_store import AccountStore
from .oauth_broker import KeyringTokenStore, OAuthBroker, build_default_oauth_configs
from .oauth_desktop import connect_in_browser
from .service_adapters import GoogleAdapter, MicrosoftAdapter, ServiceResult, YouTubeAdapter


@dataclass(frozen=True)
class AccountConnection:
    identity: AccountIdentity
    authorization_state: str


_READ_SCOPE_BY_PROVIDER: dict[ServiceProvider, tuple[tuple[str, str], ...]] = {
    ServiceProvider.GOOGLE: (
        ("https://www.googleapis.com/auth/gmail.readonly", "Read Gmail"),
        ("https://www.googleapis.com/auth/calendar.readonly", "Read Google Calendar"),
        ("https://www.googleapis.com/auth/drive.readonly", "Read Google Drive"),
    ),
    ServiceProvider.YOUTUBE: (("https://www.googleapis.com/auth/youtube.readonly", "Read YouTube channel data"),),
    ServiceProvider.MICROSOFT: (
        ("User.Read", "Read Microsoft profile"),
        ("Mail.Read", "Read Microsoft mail"),
        ("Calendars.Read", "Read Microsoft calendar"),
        ("Files.Read", "Read Microsoft files"),
    ),
}


class AccountServiceManager:
    """Coordinate persistent identities, OAuth, and guarded service adapters."""

    def __init__(
        self,
        *,
        account_access: AccountAccessRegistry | None = None,
        identities: tuple[AccountIdentity, ...] = (),
        token_broker: TokenBroker | None = None,
        account_store: AccountStore | None = None,
    ) -> None:
        self.account_store = account_store or AccountStore()
        stored = self.account_store.load()
        self._identities = tuple(identities or stored)
        self.account_access = account_access or AccountAccessRegistry()
        self._oauth = OAuthAuthorizer(DEFAULT_OAUTH_CONFIGS)
        self._token_broker = token_broker
        self._oauth_broker: OAuthBroker | None = None

    def list_accounts(self, provider: ServiceProvider | None = None) -> tuple[AccountIdentity, ...]:
        accounts = tuple(account for account in self._identities if provider is None or account.provider is provider)
        return tuple(AccountIdentity(account.provider, account.account_id, account.label, account.state) for account in accounts)

    def select_account(self, provider: ServiceProvider, *, account_id: str | None = None, label: str | None = None) -> AccountIdentity:
        return AccountSelector(self._identities).select(provider, account_id=account_id, label=label)

    def authorization_url(self, provider: ServiceProvider, *, state: str, redirect_uri: str) -> str:
        return self._oauth.authorization_request(provider, state=state, redirect_uri=redirect_uri)

    def connect_account(self, provider: ServiceProvider, *, login_hint: str | None = None) -> AccountConnection:
        """Connect one account through the system browser and persist only non-secret identity metadata."""
        identity, _token_set = connect_in_browser(self._secure_oauth(), provider, login_hint=login_hint)
        self.register_identity(identity)
        self._grant_default_read_scopes(identity)
        return AccountConnection(identity, AuthorizationState.CONNECTED.value)

    def disconnect_account(self, provider: ServiceProvider, *, account_id: str | None = None, label: str | None = None) -> None:
        identity = self.select_account(provider, account_id=account_id, label=label)
        store = KeyringTokenStore()
        store.delete(identity)
        self._identities = tuple(item for item in self._identities if item != identity)
        self.account_store.delete(identity)

    def refresh_account(self, provider: ServiceProvider, *, account_id: str | None = None, label: str | None = None) -> AccountIdentity:
        identity = self.select_account(provider, account_id=account_id, label=label)
        self._secure_oauth().refresh(identity)
        return identity

    def register_identity(self, identity: AccountIdentity) -> None:
        if any(existing.provider is identity.provider and existing.account_id == identity.account_id for existing in self._identities):
            self._identities = tuple(identity if existing.provider is identity.provider and existing.account_id == identity.account_id else existing for existing in self._identities)
        else:
            self._identities = (*self._identities, identity)
        self.account_store.upsert(identity)

    def grant_scope(self, identity: AccountIdentity, scope: str, description: str, *, risk: AccountRisk = AccountRisk.READ) -> None:
        provider = AccountProvider(identity.provider.value if identity.provider.value != "generic_web" else "generic")
        try:
            grant = self.account_access.get(provider, identity.account_id)
            scopes = [item for item in grant.scopes if item.name != scope]
            scopes.append(AccountScope(scope, description, risk))
            self.account_access._grants[(provider, identity.account_id)] = AccountGrant(provider, identity.account_id, tuple(scopes), True)
        except Exception:
            self.account_access.register(AccountGrant(provider, identity.account_id, (AccountScope(scope, description, risk),), True))

    def service_action(
        self,
        operation: str,
        *,
        provider: ServiceProvider,
        account_id: str | None = None,
        label: str | None = None,
        payload: dict[str, Any] | None = None,
        confirmed: bool = False,
    ) -> ServiceResult:
        identity = self.select_account(provider, account_id=account_id, label=label)
        adapter = {
            ServiceProvider.GOOGLE: GoogleAdapter,
            ServiceProvider.MICROSOFT: MicrosoftAdapter,
            ServiceProvider.YOUTUBE: YouTubeAdapter,
        }.get(provider)
        if adapter is None:
            raise ValueError(f"no API adapter is registered for {provider.value}")
        return adapter(self._secure_token_broker(), self.account_access).execute(operation, identity, payload, confirmed=confirmed)

    def _secure_oauth(self) -> OAuthBroker:
        if self._oauth_broker is None:
            store = KeyringTokenStore()
            configs = {config.provider: config for config in build_default_oauth_configs()}
            self._oauth_broker = OAuthBroker(configs, token_store=store)
        return self._oauth_broker

    def _secure_token_broker(self) -> TokenBroker:
        if self._token_broker is None:
            store = KeyringTokenStore()
            self._token_broker = __import__("quality_of_life.oauth_broker", fromlist=["SecureTokenBroker"]).SecureTokenBroker(self._secure_oauth(), store)
        return self._token_broker

    def _grant_default_read_scopes(self, identity: AccountIdentity) -> None:
        for scope, description in _READ_SCOPE_BY_PROVIDER.get(identity.provider, ()):
            friendly = {
                "https://www.googleapis.com/auth/gmail.readonly": "gmail.metadata",
                "https://www.googleapis.com/auth/calendar.readonly": "calendar.events.readonly",
                "https://www.googleapis.com/auth/drive.readonly": "drive.readonly",
                "https://www.googleapis.com/auth/youtube.readonly": "youtube.readonly",
            }.get(scope, scope)
            self.grant_scope(identity, friendly, description, risk=AccountRisk.READ)
