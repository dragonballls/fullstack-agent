"""Interactive desktop OAuth helper using a loopback browser callback."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .account_integrations import AccountIdentity, ServiceProvider
from .oauth_broker import OAuthBroker, OAuthPendingRequest, OAuthTokenSet


@dataclass(frozen=True)
class DesktopOAuthResult:
    identity: AccountIdentity
    provider: ServiceProvider


class _CallbackHandler(BaseHTTPRequestHandler):
    server_version = "JarvisOAuth/1.0"

    def do_GET(self) -> None:  # noqa: N802
        server: "LoopbackOAuthReceiver" = self.server.jarvis_receiver
        server.callback_url = f"http://127.0.0.1:{server.port}{self.path}"
        body = b"Jarvis authorization received. You can close this browser tab."
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        server.event.set()

    def log_message(self, format: str, *args: object) -> None:
        return


class LoopbackOAuthReceiver:
    """Listen on 127.0.0.1 only and return one OAuth callback URL."""

    def __init__(self, *, timeout_seconds: float = 300.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.event = threading.Event()
        self.callback_url: str | None = None
        self.port = 0
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "LoopbackOAuthReceiver":
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _CallbackHandler)
        self._server.daemon_threads = True
        self.port = int(self._server.server_address[1])
        self._server.jarvis_receiver = self  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._server.serve_forever, name="jarvis-oauth-loopback", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def wait_for_callback(self) -> str:
        if not self.event.wait(timeout=self.timeout_seconds):
            raise TimeoutError("OAuth browser authorization timed out")
        if not self.callback_url:
            raise RuntimeError("OAuth callback was not captured")
        return self.callback_url


def connect_in_browser(
    broker: OAuthBroker,
    provider: ServiceProvider,
    *,
    login_hint: str | None = None,
) -> tuple[AccountIdentity, OAuthTokenSet]:
    """Run one complete user-present desktop OAuth flow."""
    with LoopbackOAuthReceiver() as receiver:
        redirect_uri = f"http://127.0.0.1:{receiver.port}/oauth/callback"
        url, pending = broker.begin(provider, redirect_uri=redirect_uri, login_hint=login_hint)
        if not webbrowser.open(url, new=2):
            raise RuntimeError("could not open the system browser for OAuth authorization")
        callback_url = receiver.wait_for_callback()
        code = broker.validate_callback(callback_url, pending.state)
        token_set = broker.exchange(pending, code)
        identity = broker.user_identity(pending, token_set)
        broker.save_initial(identity, token_set)
        return identity, token_set
