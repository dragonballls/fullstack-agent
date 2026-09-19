"""Build the pinned, self-contained OmniRoute runtime used by Jarvis.exe.

The Windows release embeds Node.js 24.21.0 and OmniRoute 3.8.51 so end users
do not need to install Node or OmniRoute separately. The archive checksum is
verified before extraction and the installed OmniRoute version is verified
before the staged runtime is accepted.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.request import urlopen
from zipfile import ZipFile


NODE_VERSION = "24.21.0"
NODE_ZIP_NAME = f"node-v{NODE_VERSION}-win-x64.zip"
NODE_URL = f"https://nodejs.org/dist/v{NODE_VERSION}/{NODE_ZIP_NAME}"
NODE_SHA256 = "158f7685b44de51f6c0df1d153526cbcd3e1bc739a8dfc607721cef75de9e541"
OMNIROUTE_VERSION = "3.8.51"
OMNIROUTE_PACKAGE = f"omniroute@{OMNIROUTE_VERSION}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(path: Path) -> None:
    with urlopen(NODE_URL, timeout=180) as response, path.open("wb") as output:
        shutil.copyfileobj(response, output)


def prepare(destination: Path) -> None:
    if sys.platform != "win32":
        raise RuntimeError("The embedded OmniRoute runtime is currently a Windows release component")

    destination = destination.resolve()
    manifest = destination / "runtime-manifest.txt"
    node = destination / "node.exe"
    entry = destination / "node_modules" / "omniroute" / "bin" / "omniroute.mjs"
    if manifest.is_file() and node.is_file() and entry.is_file():
        if manifest.read_text(encoding="utf-8").strip() == f"node={NODE_VERSION}\nomniroute={OMNIROUTE_VERSION}":
            return

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="jarvis-omniroute-") as temp_name:
        temp = Path(temp_name)
        archive = temp / NODE_ZIP_NAME
        _download(archive)
        if sha256_file(archive) != NODE_SHA256:
            raise RuntimeError("Node.js archive checksum verification failed")
        extracted = temp / "node"
        with ZipFile(archive) as zip_file:
            zip_file.extractall(extracted)
        roots = [path for path in extracted.iterdir() if path.is_dir()]
        if len(roots) != 1:
            raise RuntimeError("Unexpected Node.js archive layout")
        node_root = roots[0]
        npm = node_root / "npm.cmd"
        bundled_node = node_root / "node.exe"
        if not bundled_node.is_file() or not npm.is_file():
            raise RuntimeError("Node.js runtime is incomplete")

        staging = temp / "omniroute_runtime"
        staging.mkdir()
        result = subprocess.run(
            [
                str(npm),
                "install",
                "--prefix",
                str(staging),
                "--no-fund",
                "--no-audit",
                "--omit=dev",
                OMNIROUTE_PACKAGE,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            env={**os.environ, "NODE_ENV": "production"},
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("OmniRoute package installation failed in the release build")
        shutil.copy2(bundled_node, staging / "node.exe")

        check = subprocess.run(
            [
                str(staging / "node.exe"),
                str(staging / "node_modules" / "omniroute" / "bin" / "omniroute.mjs"),
                "--version",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
            env={**os.environ, "NODE_ENV": "production"},
        )
        version = (check.stdout or "").strip()
        if check.returncode != 0 or version.splitlines()[-1:] != [OMNIROUTE_VERSION]:
            raise RuntimeError("Installed OmniRoute version did not match the pinned release")

        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(staging, destination)
        manifest = destination / "runtime-manifest.txt"
        manifest.write_text(f"node={NODE_VERSION}\nomniroute={OMNIROUTE_VERSION}\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    destination = Path(args[0]) if args else Path("build_vendor/omniroute_runtime")
    prepare(destination)
    print(f"Prepared Node {NODE_VERSION} + OmniRoute {OMNIROUTE_VERSION} at {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
