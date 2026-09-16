"""Secret-safe account identity, OAuth, and service-selection contracts for Jarvis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from urllib.parse import urlencode


class ServiceProvider(str, Enum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    GENERIC_WEB = "generic_web"


class AuthorizationState(str, Enum):
    CONNECTED = "connected"
    NEEDS_REAUTH = "needs_reauth"
    DISABLED = "disabled"
    UNCONFIGURED = "unconfigured"


class AccountIntegrationError(RuntimeError):
    """Base error for account-integration operations."""


class AccountSelectionError(AccountIntegrationError):
    """Raised when an account identity cannot be selected unambiguously."""


class OAuthConfigurationError(AccountIntegrationError):
    """Raised when an OAuth flow is not configured safely."""


@dataclass(frozen=True)
class AccountIdentity:
    """Non-secret identity metadata for one connected external account."""

    provider: ServiceProvider
    account_id: str
    label: str
    state: AuthorizationState = AuthorizationState.CONNECTED

    def __post_init__(self) -> None:
        if not self.account_id.strip():
            raise ValueError("account_id must be non-empty")
        if not self.label.strip():
            raise ValueError("label must be non-empty")


@dataclass(frozen=True)
class OAuthClientConfig:
    """Public OAuth endpoints and requested scopes; never stores a client secret."""

    provider: ServiceProvider
    authorization_url: str
    token_url: str
    client_id_env: str
    scopes: tuple[str, ...]
    extra_authorization_params: tuple[tuple[str, str], ...] = ()

    def authorization_request(self, *, state: str, redirect_uri: str) -> str:
        if not state.strip() or not redirect_uri.strip():
            raise OAuthConfigurationError("state and redirect_uri are required")
        params = dict(self.extra_authorization_params)
        params.update(
            {
                "client_id": __import__("os").environ.get(self.client_id_env, ""),
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": " ".join(self.scopes),
                "state": state,
            }
        )
        if not params["client_id"]:
            raise OAuthConfigurationError(f"missing {self.client_id_env}")
        return f"{self.authorization_url}?{urlencode(params)}"


class TokenBroker(Protocol):
    """Runtime secret store boundary. Implementations must keep tokens out of model-visible data."""

    def get_access_token(self, identity: AccountIdentity, required_scope: str) -> str: ...


class UnconfiguredTokenBroker:
    """Fail-closed token broker used until a real credential-store adapter is configured."""

    def get_access_token(self, identity: AccountIdentity, required_scope: str) -> str:
        raise OAuthConfigurationError(
            f"no credential broker is configured for {identity.provider.value}:{identity.account_id}"
        )


class OAuthAuthorizer:
    """Build authorization requests without exposing credentials or raw tokens to callers."""

    def __init__(self, configs: tuple[OAuthClientConfig, ...]) -> None:
        self._configs = {config.provider: config for config in configs}

    def authorization_request(self, provider: ServiceProvider, *, state: str, redirect_uri: str) -> str:
        try:
            config = self._configs[provider]
        except KeyError as exc:
            raise OAuthConfigurationError(f"OAuth is not configured for {provider.value}") from exc
        return config.authorization_request(state=state, redirect_uri=redirect_uri)


class AccountSelector:
    """Deterministic selector supporting multiple identities per provider."""

    def __init__(self, accounts: tuple[AccountIdentity, ...]) -> None:
        self._accounts = accounts

    def select(
        self,
        provider: ServiceProvider,
        *,
        account_id: str | None = None,
        label: str | None = None,
    ) -> AccountIdentity:
        candidates = [account for account in self._accounts if account.provider is provider and account.state is AuthorizationState.CONNECTED]
        if account_id is not None:
            candidates = [account for account in candidates if account.account_id == account_id]
        if label is not None:
            candidates = [account for account in candidates if account.label.casefold() == label.casefold()]
        if not candidates:
            raise AccountSelectionError(f"no connected {provider.value} account matches the requested identity")
        if len(candidates) > 1:
            raise AccountSelectionError(f"multiple {provider.value} accounts match; choose one explicitly")
        return candidates[0]


DEFAULT_OAUTH_CONFIGS: tuple[OAuthClientConfig, ...] = (
    OAuthClientConfig(
        provider=ServiceProvider.GOOGLE,
        authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        client_id_env="JARVIS_GOOGLE_CLIENT_ID",
        scopes=("openid", "email", "profile"),
        extra_authorization_params=(("access_type", "offline"), ("prompt", "consent")),
    ),
    OAuthClientConfig(
        provider=ServiceProvider.MICROSOFT,
        authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        client_id_env="JARVIS_MICROSOFT_CLIENT_ID",
        scopes=("openid", "profile", "email", "offline_access"),
    ),
)
