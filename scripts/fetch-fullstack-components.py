"""Fetch the pinned upstream Fullstack Agent components for a reproducible build."""

from __future__ import annotations

import json
import shutil
import sys
import urllib.request
from pathlib import Path
from zipfile import ZipFile


COMPONENTS = {
    "backtalk": {
        "repo": "jaredrhod/backtalk",
        "commit": "84b3a6cd321060cabb74aad6ebe794621cf99bd3",
    },
    "ai-visualizer": {
        "repo": "jaredrhod/ai-visualizer",
        "commit": "6921e1d4b06bdd4a34c5264882d5257c4d5f70fd",
    },
    "barehands": {
        "repo": "jaredrhod/barehands",
        "commit": "eb23bed2d772f9d5a24de26fb92f46c3c76d69cf",
    },
    "ai-memory-vault": {
        "repo": "jaredrhod/ai-memory-vault",
        "commit": "659bba9c8b351c937dd393b3042801d1ff1b502c",
    },
}


def validate_component_manifest(components: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for name, meta in components.items():
        if not meta.get("repo", "").startswith("jaredrhod/"):
            errors.append(f"{name}: repository must be jaredrhod-owned")
        commit = meta.get("commit", "")
        if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
            errors.append(f"{name}: commit must be a 40-character SHA-1")
    return errors


def _safe_extract(archive: ZipFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if target != root and root not in target.parents:
            raise RuntimeError(f"unsafe archive member: {member.filename}")
    archive.extractall(destination)


def fetch_components(destination: Path) -> dict[str, str]:
    errors = validate_component_manifest(COMPONENTS)
    if errors:
        raise ValueError("; ".join(errors))
    destination.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, str] = {}

    for name, meta in COMPONENTS.items():
        target = destination / name
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        url = f"https://github.com/{meta['repo']}/archive/{meta['commit']}.zip"
        archive_path = destination / f".{name}.zip"
        with urllib.request.urlopen(url, timeout=120) as response, archive_path.open("wb") as output:
            shutil.copyfileobj(response, output)
        with ZipFile(archive_path) as archive:
            _safe_extract(archive, target)
        archive_path.unlink(missing_ok=True)
        roots = [p for p in target.iterdir() if p.is_dir()]
        if len(roots) != 1:
            raise RuntimeError(f"{name}: unexpected archive layout")
        source_root = roots[0]
        staged = target / "source"
        source_root.rename(staged)
        manifest[name] = meta["commit"]

    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    destination = Path(args[0]) if args else Path("build_vendor")
    manifest = fetch_components(destination)
    for name, commit in manifest.items():
        print(f"{name}: {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
