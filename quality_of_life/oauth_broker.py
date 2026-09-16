"""Real desktop OAuth + secure token storage boundary for Jarvis accounts.

The broker uses authorization-code + PKCE, a loopback redirect supplied by the caller,
and an OS credential-store adapter. Tokens never enter model-visible results or local
tracked configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
import os
import secrets
from time import time
from typing import Any, Callable
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from .account_integrations import (
    AccountIdentity,
    AccountIntegrationError,
    AuthorizationState,
    OAuthClientConfig,
    OAuthConfigurationError,
    ServiceProvider,
    TokenBroker,
)


class OAuthStateError(AccountIntegrationError):
    """Raised when an OAuth callback cannot be matched to a pending request."""


class OAuthExchangeError(AccountIntegrationError):
    """Raised when an authorization code cannot be exchanged or refreshed."""


class TokenStoreError(AccountIntegrationError):
    """Raised when the configured OS credential store is unavailable."""


@dataclass(frozen=True)
class OAuthPendingRequest:
    provider: ServiceProvider
    state: str
    code_verifier: str
    redirect_uri: str
    created_at: float


@dataclass(frozen=True)
class OAuthTokenSet:
    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None
    token_type: str = "Bearer"
    scope: str | None = None

    def is_expired(self, skew_seconds: float = 60.0) -> bool:
        return self.expires_at is not None and self.expires_at <= time() + skew_seconds


class KeyringTokenStore:
    """Store OAuth token sets in the operating system credential manager via keyring."""

    SERVICE = "jarvis.external-accounts"

    def __init__(self, keyring_module: Any | None = None) -> None:
        self._keyring = keyring_module
        if self._keyring is None:
            try:
                import keyring  # type: ignore
            except ImportError as exc:
                raise TokenStoreError("keyring is not installed") from exc
            self._keyring = keyring

    @staticmethod
    def _username(identity: AccountIdentity) -> str:
        return f"{identity.provider.value}:{identity.account_id}"

    def save(self, identity: AccountIdentity, token_set: OAuthTokenSet) -> None:
        payload = json.dumps(
            {
                "access_token": token_set.access_token,
                "refresh_token": token_set.refresh_token,
                "expires_at": token_set.expires_at,
                "token_type": token_set.token_type,
                "scope": token_set.scope,
            },
            separators=(",", ":"),
        )
        try:
            self._keyring.set_password(self.SERVICE, self._username(identity), payload)
        except Exception as exc:
            raise TokenStoreError("OS credential store rejected token storage") from exc

    def load(self, identity: AccountIdentity) -> OAuthTokenSet | None:
        try:
            raw = self._keyring.get_password(self.SERVICE, self._username(identity))
        except Exception as exc:
            raise TokenStoreError("OS credential store could not be read") from exc
        if not raw:
            return None
        try:
            payload = json.loads(raw)
            return OAuthTokenSet(
                access_token=str(payload["access_token"]),
                refresh_token=str(payload["refresh_token"]) if payload.get("refresh_token") else None,
                expires_at=float(payload["expires_at"]) if payload.get("expires_at") is not None else None,
                token_type=str(payload.get("token_type") or "Bearer"),
                scope=str(payload["scope"]) if payload.get("scope") else None,
            )
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise TokenStoreError("stored OAuth token data is invalid") from exc

    def delete(self, identity: AccountIdentity) -> None:
        try:
            self._keyring.delete_password(self.SERVICE, self._username(identity))
        except Exception as exc:
            if type(exc).__name__ == "PasswordDeleteError":
                return
            raise TokenStoreError("OS credential store could not delete token") from exc


_USERINFO_URLS: dict[ServiceProvider, str] = {
    ServiceProvider.GOOGLE: "https://openidconnect.googleapis.com/v1/userinfo",
    ServiceProvider.YOUTUBE: "https://openidconnect.googleapis.com/v1/userinfo",
    ServiceProvider.MICROSOFT: "https://graph.microsoft.com/v1.0/me",
}

_SCOPE_ALIASES: dict[str, set[str]] = {
    "gmail.metadata": {"gmail.metadata", "https://www.googleapis.com/auth/gmail.metadata", "https://www.googleapis.com/auth/gmail.readonly"},
    "gmail.send": {"gmail.send", "https://www.googleapis.com/auth/gmail.send"},
    "calendar.events.readonly": {"calendar.events.readonly", "https://www.googleapis.com/auth/calendar.events.readonly", "https://www.googleapis.com/auth/calendar.readonly"},
    "drive.readonly": {"drive.readonly", "https://www.googleapis.com/auth/drive.readonly"},
    "youtube.readonly": {"youtube.readonly", "https://www.googleapis.com/auth/youtube.readonly"},
    "youtube.upload": {"youtube.upload", "https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"},
    "youtube.force-ssl": {"youtube.force-ssl", "https://www.googleapis.com/auth/youtube.force-ssl", "https://www.googleapis.com/auth/youtube"},
    "User.Read": {"User.Read", "https://graph.microsoft.com/User.Read"},
    "Mail.Read": {"Mail.Read", "https://graph.microsoft.com/Mail.Read"},
    "Mail.Send": {"Mail.Send", "https://graph.microsoft.com/Mail.Send"},
    "Calendars.Read": {"Calendars.Read", "https://graph.microsoft.com/Calendars.Read"},
    "Files.Read": {"Files.Read", "https://graph.microsoft.com/Files.Read"},
}


def scope_matches(required_scope: str, granted_scopes: str | None) -> bool:
    """Accept friendly Jarvis scope names and their provider-canonical OAuth forms."""
    if not granted_scopes:
        return True
    granted = set(granted_scopes.split())
    accepted = _SCOPE_ALIASES.get(required_scope, {required_scope})
    return bool(granted & accepted)


class OAuthBroker:
    """Desktop OAuth coordinator using PKCE and a secure token store."""

    def __init__(
        self,
        configs: dict[ServiceProvider, OAuthClientConfig],
        *,
        token_store: KeyringTokenStore,
        opener: Callable[..., object] = urlopen,
        time_fn: Callable[[], float] = time,
        pending_ttl_seconds: float = 300.0,
    ) -> None:
        if pending_ttl_seconds <= 0:
            raise ValueError("pending_ttl_seconds must be positive")
        self._configs = dict(configs)
        self._token_store = token_store
        self._opener = opener
        self._time = time_fn
        self._pending: dict[str, OAuthPendingRequest] = {}
        self._pending_ttl_seconds = pending_ttl_seconds

    @staticmethod
    def _pkce_verifier() -> str:
        return secrets.token_urlsafe(64)[:86]

    @staticmethod
    def _pkce_challenge(verifier: str) -> str:
        return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")

    @staticmethod
    def _validate_redirect_uri(redirect_uri: str) -> None:
        parsed = urlparse(redirect_uri)
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port is None
            or not 1 <= parsed.port <= 65535
            or parsed.fragment
        ):
            raise OAuthConfigurationError("desktop OAuth must use an exact 127.0.0.1 loopback redirect")

    def _purge_expired(self) -> None:
        cutoff = self._time() - self._pending_ttl_seconds
        for state, pending in tuple(self._pending.items()):
            if pending.created_at < cutoff:
                self._pending.pop(state, None)

    def begin(
        self,
        provider: ServiceProvider,
        *,
        redirect_uri: str,
        state: str | None = None,
        login_hint: str | None = None,
    ) -> tuple[str, OAuthPendingRequest]:
        config = self._configs.get(provider)
        if config is None:
            raise OAuthConfigurationError(f"OAuth is not configured for {provider.value}")
        self._validate_redirect_uri(redirect_uri)
        self._purge_expired()
        actual_state = state or secrets.token_urlsafe(32)
        if not actual_state.strip():
            raise OAuthStateError("OAuth state must be non-empty")
        verifier = self._pkce_verifier()
        pending = OAuthPendingRequest(provider, actual_state, verifier, redirect_uri, self._time())
        self._pending[actual_state] = pending
        params = {
            "client_id": os.environ.get(config.client_id_env, ""),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "state": actual_state,
            "code_challenge": self._pkce_challenge(verifier),
            "code_challenge_method": "S256",
        }
        if login_hint:
            params["login_hint"] = login_hint
        params.update(dict(config.extra_authorization_params))
        if not params["client_id"]:
            self._pending.pop(actual_state, None)
            raise OAuthConfigurationError(f"missing {config.client_id_env}")
        return f"{config.authorization_url}?{urlencode(params)}", pending

    @staticmethod
    def validate_callback(callback_url: str, expected_state: str) -> str:
        parsed = urlparse(callback_url)
        query = parse_qs(parsed.query)
        state = query.get("state", [""])[0]
        if not state or not secrets.compare_digest(state, expected_state):
            raise OAuthStateError("OAuth callback state did not match the pending request")
        error = query.get("error", [""])[0]
        if error:
            raise OAuthExchangeError(f"OAuth authorization failed: {error}")
        code = query.get("code", [""])[0]
        if not code:
            raise OAuthExchangeError("OAuth callback did not contain an authorization code")
        return code

    def exchange(self, pending: OAuthPendingRequest, code: str) -> OAuthTokenSet:
        self._purge_expired()
        config = self._configs.get(pending.provider)
        if config is None:
            raise OAuthConfigurationError(f"OAuth is not configured for {pending.provider.value}")
        current = self._pending.get(pending.state)
        if current != pending:
            raise OAuthStateError("OAuth request is unknown, expired, or already completed")
        if not code.strip():
            raise OAuthExchangeError("OAuth authorization code must be non-empty")
        payload = {
            "client_id": os.environ.get(config.client_id_env, ""),
            "code": code,
            "code_verifier": pending.code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": pending.redirect_uri,
        }
        token_set = self._post_token(config, payload)
        self._pending.pop(pending.state, None)
        return token_set

    def refresh(self, identity: AccountIdentity) -> OAuthTokenSet:
        config = self._configs.get(identity.provider)
        if config is None:
            raise OAuthConfigurationError(f"OAuth is not configured for {identity.provider.value}")
        current = self._token_store.load(identity)
        if current is None or not current.refresh_token:
            raise OAuthExchangeError("no refresh token is available for this account")
        token_set = self._post_token(
            config,
            {
                "client_id": os.environ.get(config.client_id_env, ""),
                "refresh_token": current.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if token_set.refresh_token is None:
            token_set = OAuthTokenSet(
                token_set.access_token,
                current.refresh_token,
                token_set.expires_at,
                token_set.token_type,
                token_set.scope or current.scope,
            )
        self._token_store.save(identity, token_set)
        return token_set

    def save_initial(self, identity: AccountIdentity, token_set: OAuthTokenSet) -> None:
        self._token_store.save(identity, token_set)

    def user_identity(self, pending: OAuthPendingRequest, token_set: OAuthTokenSet) -> AccountIdentity:
        url = _USERINFO_URLS.get(pending.provider)
        if url is None:
            raise OAuthConfigurationError(f"user identity lookup is not configured for {pending.provider.value}")
        request = Request(
            url,
            method="GET",
            headers={"Authorization": f"Bearer {token_set.access_token}", "Accept": "application/json", "User-Agent": "fullstack-agent-jarvis"},
        )
        try:
            with self._opener(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise OAuthExchangeError("OAuth identity lookup failed") from exc
        raw_id = data.get("sub") or data.get("id") or data.get("userPrincipalName") or data.get("mail")
        label = data.get("email") or data.get("userPrincipalName") or data.get("mail") or raw_id
        if not raw_id or not label:
            raise OAuthExchangeError("provider identity response did not contain a stable account identifier")
        return AccountIdentity(pending.provider, str(raw_id), str(label), state=AuthorizationState.CONNECTED)

    def _post_token(self, config: OAuthClientConfig, payload: dict[str, str]) -> OAuthTokenSet:
        client_id = payload.get("client_id", "")
        if not client_id:
            raise OAuthConfigurationError(f"missing {config.client_id_env}")
        request = Request(
            config.token_url,
            data=urlencode(payload).encode("utf-8"),
            method="POST",
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "fullstack-agent-jarvis"},
        )
        try:
            with self._opener(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise OAuthExchangeError("OAuth token exchange failed") from exc
        try:
            expires_in = float(data["expires_in"]) if data.get("expires_in") is not None else None
            return OAuthTokenSet(
                access_token=str(data["access_token"]),
                refresh_token=str(data["refresh_token"]) if data.get("refresh_token") else None,
                expires_at=self._time() + expires_in if expires_in is not None else None,
                token_type=str(data.get("token_type") or "Bearer"),
                scope=str(data["scope"]) if data.get("scope") else None,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise OAuthExchangeError("OAuth token response is invalid") from exc


class SecureTokenBroker(TokenBroker):
    """TokenBroker implementation that refreshes through OAuthBroker when needed."""

    def __init__(self, oauth: OAuthBroker, token_store: KeyringTokenStore) -> None:
        self._oauth = oauth
        self._store = token_store

    def get_access_token(self, identity: AccountIdentity, required_scope: str) -> str:
        token_set = self._store.load(identity)
        if token_set is None:
            raise TokenStoreError("no OAuth token is connected for this account")
        if not scope_matches(required_scope, token_set.scope):
            raise TokenStoreError("connected OAuth token does not include the requested scope")
        if token_set.is_expired():
            token_set = self._oauth.refresh(identity)
        return token_set.access_token


def build_default_oauth_configs() -> tuple[OAuthClientConfig, ...]:
    """Build complete desktop OAuth configuration for supported account providers."""
    return (
        OAuthClientConfig(
            provider=ServiceProvider.GOOGLE,
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            client_id_env="JARVIS_GOOGLE_CLIENT_ID",
            scopes=(
                "openid",
                "email",
                "profile",
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/calendar.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ),
            extra_authorization_params=(("access_type", "offline"), ("prompt", "consent")),
        ),
        OAuthClientConfig(
            provider=ServiceProvider.YOUTUBE,
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            client_id_env="JARVIS_GOOGLE_CLIENT_ID",
            scopes=(
                "openid",
                "email",
                "profile",
                "https://www.googleapis.com/auth/youtube.readonly",
                "https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.force-ssl",
            ),
            extra_authorization_params=(("access_type", "offline"), ("prompt", "consent")),
        ),
        OAuthClientConfig(
            provider=ServiceProvider.MICROSOFT,
            authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            client_id_env="JARVIS_MICROSOFT_CLIENT_ID",
            scopes=("openid", "profile", "email", "offline_access", "User.Read", "Mail.Read", "Mail.Send", "Calendars.Read", "Files.Read"),
        ),
    )
