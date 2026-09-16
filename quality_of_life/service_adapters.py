"""Guarded provider service adapters with explicit scopes and secret-safe results."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .account_integrations import AccountIdentity, ServiceProvider, TokenBroker, UnconfiguredTokenBroker
from .account_access import AccountAccessError, AccountAccessRegistry, AccountProvider


@dataclass(frozen=True)
class ServiceOperation:
    name: str
    provider: ServiceProvider
    scope: str
    method: str
    path: str
    risk: str = "read"


@dataclass(frozen=True)
class ServiceResult:
    ok: bool
    provider: ServiceProvider
    operation: str
    data: Any | None = None
    error: str | None = None


SERVICE_OPERATIONS: tuple[ServiceOperation, ...] = (
    ServiceOperation("google.gmail.profile", ServiceProvider.GOOGLE, "gmail.metadata", "GET", "https://gmail.googleapis.com/gmail/v1/users/me/profile"),
    ServiceOperation("google.calendar.events.read", ServiceProvider.GOOGLE, "calendar.events.readonly", "GET", "https://www.googleapis.com/calendar/v3/calendars/primary/events"),
    ServiceOperation("google.drive.files.read", ServiceProvider.GOOGLE, "drive.readonly", "GET", "https://www.googleapis.com/drive/v3/files"),
    ServiceOperation("microsoft.me", ServiceProvider.MICROSOFT, "User.Read", "GET", "https://graph.microsoft.com/v1.0/me"),
    ServiceOperation("microsoft.mail.read", ServiceProvider.MICROSOFT, "Mail.Read", "GET", "https://graph.microsoft.com/v1.0/me/messages"),
    ServiceOperation("microsoft.calendar.read", ServiceProvider.MICROSOFT, "Calendars.Read", "GET", "https://graph.microsoft.com/v1.0/me/events"),
    ServiceOperation("microsoft.onedrive.read", ServiceProvider.MICROSOFT, "Files.Read", "GET", "https://graph.microsoft.com/v1.0/me/drive/root/children"),
    ServiceOperation("youtube.channel", ServiceProvider.YOUTUBE, "youtube.readonly", "GET", "https://www.googleapis.com/youtube/v3/channels?part=snippet,contentDetails&mine=true"),
)

_OPERATION_INDEX = {operation.name: operation for operation in SERVICE_OPERATIONS}


class ServiceAdapterError(RuntimeError):
    """Raised for invalid or unauthorized provider service operations."""


def service_operation(name: str) -> ServiceOperation:
    try:
        return _OPERATION_INDEX[name]
    except KeyError as exc:
        raise ServiceAdapterError(f"unsupported service operation: {name}") from exc


def _map_provider(provider: ServiceProvider) -> AccountProvider:
    mapping = {
        ServiceProvider.GOOGLE: AccountProvider.GOOGLE,
        ServiceProvider.YOUTUBE: AccountProvider.YOUTUBE,
        ServiceProvider.GITHUB: AccountProvider.GITHUB,
        ServiceProvider.MICROSOFT: AccountProvider.MICROSOFT,
        ServiceProvider.INSTAGRAM: AccountProvider.INSTAGRAM,
        ServiceProvider.GENERIC_WEB: AccountProvider.GENERIC,
    }
    return mapping[provider]


class ApiServiceAdapter:
    """Small HTTP adapter that requires both local grant authorization and an OAuth token."""

    def __init__(
        self,
        token_broker: TokenBroker | None = None,
        account_access: AccountAccessRegistry | None = None,
        opener: Callable[..., object] = urlopen,
    ) -> None:
        self._token_broker = token_broker or UnconfiguredTokenBroker()
        self._account_access = account_access or AccountAccessRegistry()
        self._opener = opener

    def execute(
        self,
        operation: str,
        identity: AccountIdentity,
        payload: dict[str, Any] | None = None,
        *,
        confirmed: bool = False,
    ) -> ServiceResult:
        spec = service_operation(operation)
        if identity.provider is not spec.provider:
            return ServiceResult(False, spec.provider, operation, error="account provider does not match service operation")
        try:
            self._account_access.require(
                _map_provider(identity.provider),
                identity.account_id,
                spec.scope,
                confirmed=confirmed,
            )
            token = self._token_broker.get_access_token(identity, spec.scope)
        except AccountAccessError as exc:
            return ServiceResult(False, spec.provider, operation, error=str(exc))
        except Exception:
            return ServiceResult(False, spec.provider, operation, error="credential authorization is unavailable")

        request = Request(
            spec.path,
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            method=spec.method,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "fullstack-agent-jarvis"},
        )
        try:
            with self._opener(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, OSError, ValueError) as exc:
            return ServiceResult(False, spec.provider, operation, error=f"provider request failed: {type(exc).__name__}")
        return ServiceResult(True, spec.provider, operation, data=data)


class GoogleAdapter(ApiServiceAdapter):
    pass


class MicrosoftAdapter(ApiServiceAdapter):
    pass


class YouTubeAdapter(ApiServiceAdapter):
    pass


class GitHubAdapter(ApiServiceAdapter):
    pass


class BrowserServiceAdapter:
    """Bounded fallback contract for web services without a supported API operation."""

    def __init__(self, browser_controller: Any) -> None:
        self._browser = browser_controller

    def execute(self, url: str, *, approved_domain: str, confirmed: bool = False) -> Any:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname != approved_domain:
            raise ServiceAdapterError("browser service URL is outside the approved domain")
        if not confirmed:
            raise ServiceAdapterError("confirmation required for browser service action")
        return self._browser.open_url(url)
