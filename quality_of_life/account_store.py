"""Persistent non-secret account identity and grant metadata for Jarvis."""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
from typing import Iterable

from .account_access import AccountGrant, AccountProvider, AccountRisk, AccountScope
from .account_integrations import AccountIdentity, AuthorizationState, ServiceProvider


class AccountStore:
    """Persist account labels/IDs and permission metadata; OAuth secrets stay in the OS store."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or os.path.expanduser("~/.jarvis/accounts.json"))
        self.grants_path = self.path.with_name(f"{self.path.stem}_grants{self.path.suffix or '.json'}")

    def load(self) -> tuple[AccountIdentity, ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                return ()
            return tuple(
                AccountIdentity(
                    ServiceProvider(item["provider"]),
                    str(item["account_id"]),
                    str(item["label"]),
                    AuthorizationState(item.get("state", AuthorizationState.CONNECTED.value)),
                )
                for item in payload
                if isinstance(item, dict)
            )
        except (OSError, ValueError, KeyError):
            return ()

    def save(self, identities: Iterable[AccountIdentity]) -> None:
        self._atomic_write(self.path, [asdict(identity) | {"provider": identity.provider.value, "state": identity.state.value} for identity in identities])

    def upsert(self, identity: AccountIdentity) -> tuple[AccountIdentity, ...]:
        identities = [item for item in self.load() if not (item.provider is identity.provider and item.account_id == identity.account_id)]
        identities.append(identity)
        self.save(identities)
        return tuple(identities)

    def delete(self, identity: AccountIdentity) -> tuple[AccountIdentity, ...]:
        identities = tuple(item for item in self.load() if not (item.provider is identity.provider and item.account_id == identity.account_id))
        self.save(identities)
        self.delete_grant(identity)
        return identities

    def load_grants(self) -> tuple[AccountGrant, ...]:
        if not self.grants_path.exists():
            return ()
        try:
            payload = json.loads(self.grants_path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                return ()
            result: list[AccountGrant] = []
            for item in payload:
                if not isinstance(item, dict):
                    continue
                scopes = tuple(
                    AccountScope(str(scope["name"]), str(scope.get("description", "")), AccountRisk(str(scope.get("risk", "read"))))
                    for scope in item.get("scopes", [])
                    if isinstance(scope, dict)
                )
                result.append(AccountGrant(AccountProvider(str(item["provider"])), str(item["account_id"]), scopes, bool(item.get("enabled", True))))
            return tuple(result)
        except (OSError, ValueError, KeyError):
            return ()

    def save_grants(self, grants: Iterable[AccountGrant]) -> None:
        payload = [
            {
                "provider": grant.provider.value,
                "account_id": grant.account_id,
                "enabled": grant.enabled,
                "scopes": [asdict(scope) | {"risk": scope.risk.value} for scope in grant.scopes],
            }
            for grant in grants
        ]
        self._atomic_write(self.grants_path, payload)

    def save_grant(self, grant: AccountGrant, grants: Iterable[AccountGrant]) -> None:
        self.save_grants(grants)

    def delete_grant(self, identity: AccountIdentity) -> None:
        remaining = tuple(
            grant for grant in self.load_grants()
            if not (grant.provider.value == identity.provider.value and grant.account_id == identity.account_id)
        )
        self.save_grants(remaining)

    @staticmethod
    def _atomic_write(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
            json.dump(payload, tmp, indent=2, sort_keys=True)
            tmp.flush()
            os.fsync(tmp.fileno())
            temporary = Path(tmp.name)
        os.replace(temporary, path)
