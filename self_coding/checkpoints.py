"""Persistent, reversible checkpoints for guarded self-coding.

Checkpoint state lives outside the repository so tracking it never dirties the
working tree. Git refs remain the source of truth for the actual code state.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def default_state_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_STATE_HOME")
    if root:
        return Path(root) / "FullstackAgent" / "self-coding"
    return Path.home() / ".fullstack-agent" / "self-coding"


@dataclass
class CheckpointRecord:
    checkpoint_id: str
    repo: str
    original_branch: str
    baseline_commit: str
    preview_branch: str
    checkpoint_tag: str
    created_at: str
    updated_at: str
    status: str = "preview"
    commits: list[str] = field(default_factory=list)
    published_head: str | None = None
    revert_commit: str | None = None


class CheckpointStore:
    """Small JSON journal for the current and previous self-coding checkpoints."""

    def __init__(self, state_dir: Path | None = None) -> None:
        self.state_dir = (state_dir or default_state_dir()).expanduser().resolve()
        self.path = self.state_dir / "checkpoints.json"

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unable to read self-coding checkpoint state: {exc}") from exc
        if not isinstance(raw, list):
            raise RuntimeError("Self-coding checkpoint state is malformed.")
        return [item for item in raw if isinstance(item, dict)]

    def _save(self, records: list[dict[str, Any]]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(records, indent=2, sort_keys=True) + "\n"
        fd, tmp_name = tempfile.mkstemp(prefix="checkpoints-", suffix=".tmp", dir=self.state_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            Path(tmp_name).replace(self.path)
        finally:
            try:
                Path(tmp_name).unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _record(item: dict[str, Any]) -> CheckpointRecord:
        return CheckpointRecord(
            checkpoint_id=str(item["checkpoint_id"]),
            repo=str(item["repo"]),
            original_branch=str(item["original_branch"]),
            baseline_commit=str(item["baseline_commit"]),
            preview_branch=str(item["preview_branch"]),
            checkpoint_tag=str(item["checkpoint_tag"]),
            created_at=str(item["created_at"]),
            updated_at=str(item["updated_at"]),
            status=str(item.get("status", "preview")),
            commits=[str(value) for value in item.get("commits", [])],
            published_head=str(item["published_head"]) if item.get("published_head") else None,
            revert_commit=str(item["revert_commit"]) if item.get("revert_commit") else None,
        )

    def active_preview(self, repo: Path) -> CheckpointRecord | None:
        target = str(repo.resolve())
        records = self._load()
        for item in reversed(records):
            if str(item.get("repo")) == target and item.get("status") == "preview":
                return self._record(item)
        return None

    def latest_published(self, repo: Path) -> CheckpointRecord | None:
        target = str(repo.resolve())
        records = self._load()
        for item in reversed(records):
            if str(item.get("repo")) == target and item.get("status") == "published":
                return self._record(item)
        return None

    def has_active_preview(self, repo: Path) -> bool:
        return self.active_preview(repo) is not None

    def add(self, record: CheckpointRecord) -> None:
        records = self._load()
        records.append(asdict(record))
        self._save(records)

    def update(self, checkpoint_id: str, **changes: Any) -> CheckpointRecord:
        records = self._load()
        for item in records:
            if item.get("checkpoint_id") == checkpoint_id:
                item.update(changes)
                item["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save(records)
                return self._record(item)
        raise RuntimeError(f"Unknown self-coding checkpoint: {checkpoint_id}")

    def next_id(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


__all__ = ["CheckpointRecord", "CheckpointStore", "default_state_dir"]
