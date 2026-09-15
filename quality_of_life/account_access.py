"""User-authorized external account access contracts.

Credentials are never stored in this module. Integrations resolve credentials through
an external secret/OAuth mechanism and expose only the minimum capability needed for a
request. Consequential actions remain confirmation-gated by the runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


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
    """Raised when an account operation is not authorized by the local grant."""


class AccountAccessRegistry:
    """Explicit registry of accounts Jarvis is allowed to act through."""

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
