"""Guarded filesystem capability with explicit target validation."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .permissions import Capability, CapabilityPolicy


class FilesystemError(RuntimeError):
    """Raised for invalid, protected, or unverifiable filesystem operations."""


@dataclass(frozen=True)
class FileInfo:
    path: Path
    exists: bool
    is_file: bool
    is_dir: bool
    size: int


class FileController:
    def __init__(self, policy: CapabilityPolicy, roots: Iterable[Path] | None = None) -> None:
        self.policy = policy
        self.roots = tuple(Path(root).expanduser().resolve() for root in (roots or (Path.home(),)))

    def _target(self, value: str | Path) -> Path:
        path = Path(value).expanduser()
        try:
            resolved = path.resolve(strict=False)
        except OSError as exc:
            raise FilesystemError(f"Unable to normalize path: {value}") from exc
        if any(resolved == root or root in resolved.parents for root in self.roots):
            return resolved
        raise FilesystemError("Path is outside permitted filesystem roots")

    def _reject_protected(self, path: Path) -> None:
        protected = {Path(os.environ.get("WINDIR", r"C:\Windows")).resolve(), Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")).resolve()}
        if any(path == root or root in path.parents for root in protected):
            raise FilesystemError("Protected system location")

    @staticmethod
    def _info(target: Path) -> FileInfo:
        return FileInfo(target, target.exists(), target.is_file(), target.is_dir(), target.stat().st_size if target.is_file() else 0)

    def info(self, path: str | Path) -> FileInfo:
        self.policy.check(Capability.FILE_READ)
        target = self._target(path)
        return self._info(target)

    def search(self, pattern: str, root: str | Path | None = None, limit: int = 100) -> tuple[Path, ...]:
        self.policy.check(Capability.FILE_READ)
        if not pattern or limit < 1 or limit > 1000:
            raise ValueError("pattern must be non-empty and limit must be between 1 and 1000")
        base = self._target(root or self.roots[0])
        if not base.is_dir():
            raise FilesystemError("Search root is not a directory")
        return tuple(sorted(base.rglob(pattern), key=lambda p: str(p).casefold())[:limit])

    def read_text(self, path: str | Path, max_bytes: int = 5_000_000) -> str:
        self.policy.check(Capability.FILE_READ)
        if max_bytes < 1 or max_bytes > 50_000_000:
            raise ValueError("max_bytes is outside the supported range")
        target = self._target(path)
        if not target.is_file():
            raise FilesystemError("File does not exist")
        if target.stat().st_size > max_bytes:
            raise FilesystemError("File exceeds the read size limit")
        return target.read_text(encoding="utf-8")

    def write_text(self, path: str | Path, text: str) -> FileInfo:
        self.policy.check(Capability.FILE_WRITE)
        target = self._target(path)
        self._reject_protected(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        if not target.is_file():
            raise FilesystemError("Write could not be verified")
        return self._info(target)

    def copy(self, source: str | Path, destination: str | Path) -> FileInfo:
        self.policy.check(Capability.FILE_WRITE)
        src, dst = self._target(source), self._target(destination)
        self._reject_protected(dst)
        if not src.exists():
            raise FilesystemError("Source does not exist")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=False)
        else:
            shutil.copy2(src, dst)
        if not dst.exists():
            raise FilesystemError("Copy could not be verified")
        return self._info(dst)

    def move(self, source: str | Path, destination: str | Path) -> FileInfo:
        self.policy.check(Capability.FILE_WRITE)
        src, dst = self._target(source), self._target(destination)
        self._reject_protected(dst)
        if not src.exists():
            raise FilesystemError("Source does not exist")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        if src.exists() or not dst.exists():
            raise FilesystemError("Move could not be verified")
        return self._info(dst)

    def delete(self, path: str | Path) -> bool:
        self.policy.check(Capability.FILE_DELETE)
        target = self._target(path)
        self._reject_protected(target)
        if target == target.anchor or target == Path.home().resolve():
            raise FilesystemError("Refusing to delete an ambiguous root/home target")
        if not target.exists():
            return True
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        if target.exists():
            raise FilesystemError("Delete could not be verified")
        return True
