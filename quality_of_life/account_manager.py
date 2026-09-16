"""Unified multi-account manager for Jarvis external services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .account_access import AccountAccessRegistry
from .account_integrations import (
    AccountIdentity,
    AccountSelector,
    DEFAULT_OAUTH_CONFIGS,
    OAuthAuthorizer,
    ServiceProvider,
    TokenBroker,
)
from .service_adapters import GoogleAdapter, MicrosoftAdapter, ServiceResult, YouTubeAdapter


@dataclass(frozen=True)
class AccountConnection:
    identity: AccountIdentity
    authorization_state: str


class AccountServiceManager:
    """Coordinate identity selection, OAuth handoff, and guarded service adapters."""

    def __init__(
        self,
        *,
        account_access: AccountAccessRegistry | None = None,
        identities: tuple[AccountIdentity, ...] = (),
        token_broker: TokenBroker | None = None,
    ) -> None:
        self.account_access = account_access or AccountAccessRegistry()
        self._identities = tuple(identities)
        self._oauth = OAuthAuthorizer(DEFAULT_OAUTH_CONFIGS)
        self._token_broker = token_broker

    def list_accounts(self, provider: ServiceProvider | None = None) -> tuple[AccountIdentity, ...]:
        accounts = tuple(account for account in self._identities if provider is None or account.provider is provider)
        return tuple(
            AccountIdentity(account.provider, account.account_id, account.label, account.state)
            for account in accounts
        )

    def select_account(
        self,
        provider: ServiceProvider,
        *,
        account_id: str | None = None,
        label: str | None = None,
    ) -> AccountIdentity:
        return AccountSelector(self._identities).select(provider, account_id=account_id, label=label)

    def authorization_url(self, provider: ServiceProvider, *, state: str, redirect_uri: str) -> str:
        return self._oauth.authorization_request(provider, state=state, redirect_uri=redirect_uri)

    def register_identity(self, identity: AccountIdentity) -> None:
        if any(existing.provider is identity.provider and existing.account_id == identity.account_id for existing in self._identities):
            raise ValueError("account identity already registered")
        self._identities = (*self._identities, identity)

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
        if self._token_broker is None:
            raise RuntimeError("account credential broker is not configured")
        adapter = {
            ServiceProvider.GOOGLE: GoogleAdapter,
            ServiceProvider.MICROSOFT: MicrosoftAdapter,
            ServiceProvider.YOUTUBE: YouTubeAdapter,
        }.get(provider)
        if adapter is None:
            raise ValueError(f"no API adapter is registered for {provider.value}")
        return adapter(self._token_broker, self.account_access).execute(
            operation,
            identity,
            payload,
            confirmed=confirmed,
        )
