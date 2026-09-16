"""Guarded provider service adapters with explicit scopes and secret-safe results."""

from __future__ import annotations

from dataclasses import dataclass
import base64
import json
from email.message import EmailMessage
from pathlib import Path
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
    ServiceOperation("google.gmail.send", ServiceProvider.GOOGLE, "gmail.send", "POST", "https://gmail.googleapis.com/gmail/v1/users/me/messages/send", "write"),
    ServiceOperation("google.calendar.events.read", ServiceProvider.GOOGLE, "calendar.events.readonly", "GET", "https://www.googleapis.com/calendar/v3/calendars/primary/events"),
    ServiceOperation("google.drive.files.read", ServiceProvider.GOOGLE, "drive.readonly", "GET", "https://www.googleapis.com/drive/v3/files"),
    ServiceOperation("microsoft.me", ServiceProvider.MICROSOFT, "User.Read", "GET", "https://graph.microsoft.com/v1.0/me"),
    ServiceOperation("microsoft.mail.read", ServiceProvider.MICROSOFT, "Mail.Read", "GET", "https://graph.microsoft.com/v1.0/me/messages"),
    ServiceOperation("microsoft.mail.send", ServiceProvider.MICROSOFT, "Mail.Send", "POST", "https://graph.microsoft.com/v1.0/me/sendMail", "write"),
    ServiceOperation("microsoft.calendar.read", ServiceProvider.MICROSOFT, "Calendars.Read", "GET", "https://graph.microsoft.com/v1.0/me/events"),
    ServiceOperation("microsoft.onedrive.read", ServiceProvider.MICROSOFT, "Files.Read", "GET", "https://graph.microsoft.com/v1.0/me/drive/root/children"),
    ServiceOperation("youtube.channel", ServiceProvider.YOUTUBE, "youtube.readonly", "GET", "https://www.googleapis.com/youtube/v3/channels?part=snippet,contentDetails&mine=true"),
    ServiceOperation("youtube.video.upload", ServiceProvider.YOUTUBE, "youtube.upload", "UPLOAD", "https://www.googleapis.com/upload/youtube/v3/videos", "write"),
    ServiceOperation("youtube.video.update", ServiceProvider.YOUTUBE, "youtube.force-ssl", "PUT", "https://www.googleapis.com/youtube/v3/videos?part=snippet,status", "write"),
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


def _json_request(url: str, token: str, method: str, payload: dict[str, Any] | None = None) -> Request:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "fullstack-agent-jarvis",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    return Request(url, data=body, method=method, headers=headers)


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

        if spec.method == "UPLOAD":
            return self._youtube_upload(spec, operation, identity, token, payload or {})
        if operation == "google.gmail.send":
            return self._gmail_send(spec, operation, token, payload or {})
        if operation == "microsoft.mail.send":
            return self._microsoft_send(spec, operation, token, payload or {})
        request = _json_request(spec.path, token, spec.method, payload)
        try:
            with self._opener(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw) if raw else None
        except (HTTPError, URLError, OSError, ValueError) as exc:
            return ServiceResult(False, spec.provider, operation, error=f"provider request failed: {type(exc).__name__}")
        return ServiceResult(True, spec.provider, operation, data=data)

    def _gmail_send(self, spec: ServiceOperation, operation: str, token: str, payload: dict[str, Any]) -> ServiceResult:
        to = payload.get("to")
        subject = payload.get("subject")
        body = payload.get("body")
        if not isinstance(to, str) or not to.strip() or not isinstance(subject, str) or not isinstance(body, str):
            return ServiceResult(False, spec.provider, operation, error="gmail send requires to, subject, and body")
        message = EmailMessage()
        message["To"] = to.strip()
        message["Subject"] = subject
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")
        request = _json_request(spec.path, token, spec.method, {"raw": raw})
        try:
            with self._opener(request, timeout=20) as response:
                raw_response = response.read().decode("utf-8")
                data = json.loads(raw_response) if raw_response else None
        except (HTTPError, URLError, OSError, ValueError) as exc:
            return ServiceResult(False, spec.provider, operation, error=f"provider request failed: {type(exc).__name__}")
        return ServiceResult(True, spec.provider, operation, data=data)

    def _microsoft_send(self, spec: ServiceOperation, operation: str, token: str, payload: dict[str, Any]) -> ServiceResult:
        to = payload.get("to")
        subject = payload.get("subject")
        body = payload.get("body")
        if not isinstance(to, str) or not to.strip() or not isinstance(subject, str) or not isinstance(body, str):
            return ServiceResult(False, spec.provider, operation, error="microsoft mail send requires to, subject, and body")
        message = {
            "message": {
                "subject": subject,
                "body": {"contentType": str(payload.get("content_type") or "Text"), "content": body},
                "toRecipients": [{"emailAddress": {"address": to.strip()}}],
            },
            "saveToSentItems": bool(payload.get("save_to_sent_items", True)),
        }
        request = _json_request(spec.path, token, spec.method, message)
        try:
            with self._opener(request, timeout=20) as response:
                raw_response = response.read().decode("utf-8")
                data = json.loads(raw_response) if raw_response else {"accepted": True}
        except (HTTPError, URLError, OSError, ValueError) as exc:
            return ServiceResult(False, spec.provider, operation, error=f"provider request failed: {type(exc).__name__}")
        return ServiceResult(True, spec.provider, operation, data=data)

    def _youtube_upload(self, spec: ServiceOperation, operation: str, identity: AccountIdentity, token: str, payload: dict[str, Any]) -> ServiceResult:
        path_value = payload.get("file_path")
        title = payload.get("title")
        if not isinstance(path_value, str) or not path_value.strip() or not isinstance(title, str) or not title.strip():
            return ServiceResult(False, spec.provider, operation, error="youtube upload requires file_path and title")
        path = Path(path_value).expanduser()
        if not path.is_file():
            return ServiceResult(False, spec.provider, operation, error="youtube upload file does not exist")
        mime = str(payload.get("mime_type") or "video/mp4")
        metadata = {
            "snippet": {
                "title": title.strip(),
                "description": str(payload.get("description") or ""),
                "tags": [str(tag) for tag in payload.get("tags", [])] if isinstance(payload.get("tags", []), list) else [],
                "categoryId": str(payload.get("category_id") or "22"),
            },
            "status": {
                "privacyStatus": str(payload.get("privacy") or "private"),
                "selfDeclaredMadeForKids": bool(payload.get("made_for_kids", False)),
            },
        }
        start = Request(
            spec.path + "?part=snippet,status",
            data=json.dumps(metadata).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Length": str(path.stat().st_size),
                "X-Upload-Content-Type": mime,
                "User-Agent": "fullstack-agent-jarvis",
            },
        )
        try:
            with self._opener(start, timeout=20) as response:
                upload_url = response.headers.get("Location")
                if not upload_url:
                    return ServiceResult(False, spec.provider, operation, error="youtube upload session URL was not returned")
            upload_request = Request(
                upload_url,
                data=path.read_bytes(),
                method="PUT",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": mime,
                    "Content-Length": str(path.stat().st_size),
                    "User-Agent": "fullstack-agent-jarvis",
                },
            )
            with self._opener(upload_request, timeout=max(60, min(900, int(path.stat().st_size / 100_000) + 60))) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw) if raw else None
        except (HTTPError, URLError, OSError, ValueError) as exc:
            return ServiceResult(False, spec.provider, operation, error=f"youtube upload failed: {type(exc).__name__}")
        return ServiceResult(True, identity.provider, operation, data=data)


class GoogleAdapter(ApiServiceAdapter):
    pass


class MicrosoftAdapter(ApiServiceAdapter):
    pass


class YouTubeAdapter(ApiServiceAdapter):
    pass


class GitHubAdapter(ApiServiceAdapter):
    pass


class BrowserServiceAdapter:
    """Bounded fallback for web services without a supported API operation."""

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
