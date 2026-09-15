"""Authorized external-account integrations for Jarvis.

Credentials are resolved at call time from an external secret/OAuth mechanism and are
never persisted, returned, or logged here. The local account grant remains the source
of truth for what Jarvis may do with an account.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import os
import re
from typing import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AccountProvider(str, Enum):
    GITHUB = "github"
    GOOGLE = "google"
    YOUTUBE = "youtube"
    GENERIC = "generic"


class AccountRisk(str, Enum):
    READ = "read"
    WRITE = "write"
    FINANCIAL = "financial"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class AccountScope:
    name: str
    description: str
    risk: AccountRisk = AccountRisk.READ


@dataclass(frozen=True)
class AccountGrant:
    provider: AccountProvider
    account_id: str
    scopes: tuple[AccountScope, ...] = field(default_factory=tuple)
    enabled: bool = True

    def allows(self, scope_name: str) -> bool:
        return self.enabled and any(scope.name == scope_name for scope in self.scopes)

    def requires_confirmation(self, scope_name: str) -> bool:
        for scope in self.scopes:
            if scope.name == scope_name:
                return scope.risk is not AccountRisk.READ
        return True


class AccountAccessError(RuntimeError):
    """Raised when an account operation is not authorized."""


class AccountAccessRegistry:
    """Explicit registry of accounts Jarvis may act through."""

    def __init__(self, grants: Iterable[AccountGrant] = ()) -> None:
        self._grants: dict[tuple[AccountProvider, str], AccountGrant] = {}
        for grant in grants:
            self.register(grant)

    def register(self, grant: AccountGrant) -> None:
        key = (grant.provider, grant.account_id)
        if key in self._grants:
            raise ValueError(f"account grant already registered: {grant.provider.value}:{grant.account_id}")
        self._grants[key] = grant

    def get(self, provider: AccountProvider, account_id: str) -> AccountGrant:
        try:
            grant = self._grants[(provider, account_id)]
        except KeyError as exc:
            raise AccountAccessError(f"account not authorized: {provider.value}:{account_id}") from exc
        if not grant.enabled:
            raise AccountAccessError(f"account access disabled: {provider.value}:{account_id}")
        return grant

    def require(self, provider: AccountProvider, account_id: str, scope_name: str, *, confirmed: bool = False) -> AccountGrant:
        grant = self.get(provider, account_id)
        if not grant.allows(scope_name):
            raise AccountAccessError(f"scope not authorized: {provider.value}:{account_id}:{scope_name}")
        if grant.requires_confirmation(scope_name) and not confirmed:
            raise AccountAccessError(f"confirmation required: {provider.value}:{account_id}:{scope_name}")
        return grant

    def list_accounts(self) -> tuple[AccountGrant, ...]:
        return tuple(self._grants.values())


class GitHubRepositoryError(RuntimeError):
    """Raised when a GitHub repository operation cannot be completed."""


_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class GitHubRepositoryClient:
    """Minimal GitHub repository client using a caller-supplied credential resolver."""

    def __init__(
        self,
        token_resolver: Callable[[], str | None] | None = None,
        opener: Callable[..., object] = urlopen,
    ) -> None:
        self._token_resolver = token_resolver or (lambda: os.getenv("GITHUB_TOKEN"))
        self._opener = opener

    @staticmethod
    def _validate_repo(repository: str) -> tuple[str, str]:
        normalized = repository.removeprefix("https://github.com/").removeprefix("http://github.com/").strip("/")
        if normalized.endswith(".git"):
            normalized = normalized[:-4]
        if not _REPO_RE.fullmatch(normalized):
            raise GitHubRepositoryError("repository must be an owner/name GitHub repository")
        owner, name = normalized.split("/", 1)
        return owner, name

    def fork_repository(
        self,
        repository: str,
        *,
        account_id: str,
        access: AccountAccessRegistry,
        confirmed: bool = False,
        organization: str | None = None,
    ) -> dict[str, str]:
        access.require(AccountProvider.GITHUB, account_id, "repo.fork", confirmed=confirmed)
        owner, name = self._validate_repo(repository)
        token = self._token_resolver()
        if not token:
            raise GitHubRepositoryError("GitHub credential is not configured")
        payload: dict[str, str] = {}
        if organization:
            if not re.fullmatch(r"^[A-Za-z0-9_.-]+$", organization):
                raise GitHubRepositoryError("invalid GitHub organization name")
            payload["organization"] = organization
        request = Request(
            f"https://api.github.com/repos/{owner}/{name}/forks",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "fullstack-agent-jarvis",
            },
        )
        try:
            with self._opener(request, timeout=20) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, OSError, ValueError) as exc:
            raise GitHubRepositoryError("GitHub fork request failed") from exc
        return {key: str(result[key]) for key in ("full_name", "html_url", "clone_url") if result.get(key)}
