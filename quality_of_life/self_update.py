"""Guarded GitHub release updater for the single-file Windows Jarvis app."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_REPOSITORY = "dragonballls/fullstack-agent"
DEFAULT_RELEASE_API = f"https://api.github.com/repos/{DEFAULT_REPOSITORY}/releases/tags/latest"


class SelfUpdateError(RuntimeError):
    """Raised when an update cannot be safely prepared."""


@dataclass(frozen=True)
class GitHubRelease:
    tag_name: str
    commit_sha: str
    asset_url: str
    sha256: str

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "GitHubRelease":
        tag_name = str(payload.get("tag_name") or "").strip()
        body = str(payload.get("body") or "")
        commit_sha = ""
        for line in body.splitlines():
            if line.strip().lower().startswith("commit:"):
                commit_sha = line.split(":", 1)[1].strip()
                break
        assets = payload.get("assets")
        if not isinstance(assets, list):
            raise SelfUpdateError("GitHub release has no assets list")
        exe_asset: dict[str, object] | None = None
        for asset in assets:
            if isinstance(asset, dict) and str(asset.get("name") or "") == "Jarvis.exe":
                exe_asset = asset
                break
        if not tag_name or not commit_sha or exe_asset is None:
            raise SelfUpdateError("latest release is missing Jarvis.exe or its commit identifier")
        asset_url = str(exe_asset.get("browser_download_url") or "").strip()
        digest = str(exe_asset.get("digest") or "").strip().lower()
        if digest.startswith("sha256:"):
            digest = digest[7:]
        if not asset_url or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise SelfUpdateError("latest Jarvis.exe asset has no valid SHA-256 digest")
        parsed = urlparse(asset_url)
        if parsed.scheme != "https" or parsed.netloc != "github.com" or "/releases/download/" not in parsed.path:
            raise SelfUpdateError("update asset URL is not an HTTPS GitHub release download")
        return cls(tag_name=tag_name, commit_sha=commit_sha, asset_url=asset_url, sha256=digest)


def is_update_available(current_commit: str, release_commit: str) -> bool:
    current = current_commit.strip()
    release = release_commit.strip()
    return bool(current and release and current != release)


def verify_sha256(path: Path, expected: str) -> bool:
    expected = expected.strip().lower()
    if len(expected) != 64:
        return False
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return False
    return digest.hexdigest() == expected


def fetch_latest_release(url: str = DEFAULT_RELEASE_API, timeout: float = 15.0) -> GitHubRelease:
    request = Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Jarvis-Updater"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise SelfUpdateError(f"could not read latest Jarvis release: {exc}") from exc
    if not isinstance(payload, dict):
        raise SelfUpdateError("GitHub release response was not an object")
    return GitHubRelease.from_payload(payload)


def build_windows_handoff_script(pid: int, current_exe: Path, staged_exe: Path) -> str:
    """Return a hidden PowerShell handoff used only after the app exits."""
    current = str(current_exe)
    staged = str(staged_exe)
    return "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f"$pidToWait = {int(pid)}",
            f"$current = '{current.replace(chr(39), chr(39) + chr(39))}'",
            f"$staged = '{staged.replace(chr(39), chr(39) + chr(39))}'",
            "$replaced = $false",
            "try {",
            "  Wait-Process -Id $pidToWait -Timeout 60 -ErrorAction Stop",
            "} catch { Start-Sleep -Seconds 2 }",
            "for ($i = 0; $i -lt 30; $i++) {",
            "  try {",
            "    Move-Item -LiteralPath $staged -Destination $current -Force",
            "    $replaced = $true",
            "    break",
            "  }",
            "  catch { Start-Sleep -Seconds 1 }",
            "}",
            "if (-not $replaced) { exit 1 }",
            "if (-not (Test-Path -LiteralPath $current)) { exit 1 }",
            "Start-Process -FilePath $current",
            "Remove-Item -LiteralPath $staged -Force -ErrorAction SilentlyContinue",
        ]
    )


def stage_update(asset_url: str, expected_sha256: str, destination: Path, timeout: float = 120.0) -> Path:
    parsed = urlparse(asset_url)
    if parsed.scheme != "https" or parsed.netloc != "github.com" or not parsed.path.endswith("/Jarvis.exe"):
        raise SelfUpdateError("refusing to download from an untrusted update URL")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(asset_url, headers={"User-Agent": "Jarvis-Updater"}, method="GET")
    temporary = destination.with_suffix(destination.suffix + ".download")
    try:
        with urlopen(request, timeout=timeout) as response, temporary.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
        if not verify_sha256(temporary, expected_sha256):
            raise SelfUpdateError("downloaded Jarvis.exe failed SHA-256 verification")
        os.replace(temporary, destination)
        return destination
    except SelfUpdateError:
        temporary.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        raise SelfUpdateError(f"could not stage Jarvis.exe update: {exc}") from exc
