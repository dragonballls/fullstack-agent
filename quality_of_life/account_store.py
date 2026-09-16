"""Persistent non-secret account identity metadata for Jarvis."""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
from typing import Iterable

from .account_integrations import AccountIdentity, AuthorizationState, ServiceProvider


class AccountStore:
    """Persist account labels/IDs without persisting OAuth secrets."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or os.path.expanduser("~/.jarvis/accounts.json"))

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
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(identity) | {"provider": identity.provider.value, "state": identity.state.value} for identity in identities]
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(self.path.parent), delete=False) as tmp:
            json.dump(payload, tmp, indent=2, sort_keys=True)
            tmp.flush()
            os.fsync(tmp.fileno())
            temporary = Path(tmp.name)
        os.replace(temporary, self.path)

    def upsert(self, identity: AccountIdentity) -> tuple[AccountIdentity, ...]:
        identities = [item for item in self.load() if not (item.provider is identity.provider and item.account_id == identity.account_id)]
        identities.append(identity)
        self.save(identities)
        return tuple(identities)

    def delete(self, identity: AccountIdentity) -> tuple[AccountIdentity, ...]:
        identities = tuple(item for item in self.load() if not (item.provider is identity.provider and item.account_id == identity.account_id))
        self.save(identities)
        return identities
