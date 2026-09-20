"""Build the pinned, self-contained OmniRoute runtime used by Jarvis.exe.

OmniRoute 3.8.50 is the current official published Windows release,
so the release bundle is sourced from its exact immutable commit instead of
assuming the version already exists on npm. The resulting local package is
installed with production dependencies and verified before packaging.
"""

from __future__ import annotations

import hashlib
import json
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
OMNIROUTE_VERSION = "3.8.50"
OMNIROUTE_COMMIT = "5458026c216f77a3da68ea49152dc33470cfe2cb"
OMNIROUTE_SOURCE_URL = f"https://github.com/diegosouzapw/OmniRoute/archive/{OMNIROUTE_COMMIT}.zip"
RUNTIME_CACHE_SCHEMA = "5"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, path: Path) -> None:
    with urlopen(url, timeout=180) as response, path.open("wb") as output:
        shutil.copyfileobj(response, output)


def _single_extracted_root(directory: Path) -> Path:
    roots = [path for path in directory.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise RuntimeError("Unexpected OmniRoute/Node archive layout")
    return roots[0]


def _native_load_ok(node: Path, native: Path) -> bool:
    if not node.is_file() or not native.is_file():
        return False
    try:
        result = subprocess.run(
            [
                str(node),
                "-e",
                "const p=process.argv[1]; process.dlopen({exports:{}},p); console.log('native-ok')",
                str(native),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
            env={**os.environ, "NODE_ENV": "production"},
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and "native-ok" in (result.stdout or "")


def _runtime_is_healthy(destination: Path) -> bool:
    node = destination / "node.exe"
    entry = destination / "node_modules" / "omniroute" / "bin" / "omniroute.mjs"
    native = (
        destination
        / "node_modules"
        / "omniroute"
        / "dist"
        / "node_modules"
        / "better-sqlite3"
        / "build"
        / "Release"
        / "better_sqlite3.node"
    )
    if not _native_load_ok(node, native) or not entry.is_file():
        return False
    try:
        check = subprocess.run(
            [str(node), str(entry), "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
            env={**os.environ, "NODE_ENV": "production"},
        )
    except (OSError, subprocess.SubprocessError):
        return False
    version = (check.stdout or "").strip()
    return check.returncode == 0 and version.splitlines()[-1:] == [OMNIROUTE_VERSION]


def prepare(destination: Path) -> None:
    if sys.platform != "win32":
        raise RuntimeError("The embedded OmniRoute runtime is currently a Windows release component")

    destination = destination.resolve()
    manifest = destination / "runtime-manifest.txt"
    node = destination / "node.exe"
    entry = destination / "node_modules" / "omniroute" / "bin" / "omniroute.mjs"
    if manifest.is_file() and node.is_file() and entry.is_file():
        expected = (
            f"schema={RUNTIME_CACHE_SCHEMA}\n"
            f"node={NODE_VERSION}\n"
            f"omniroute={OMNIROUTE_VERSION}\n"
            f"commit={OMNIROUTE_COMMIT}\n"
        )
        if manifest.read_text(encoding="utf-8") == expected and _runtime_is_healthy(destination):
            return
        shutil.rmtree(destination, ignore_errors=True)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="jarvis-omniroute-", ignore_cleanup_errors=True) as temp_name:
        temp = Path(temp_name)

        node_archive = temp / NODE_ZIP_NAME
        _download(NODE_URL, node_archive)
        if sha256_file(node_archive) != NODE_SHA256:
            raise RuntimeError("Node.js archive checksum verification failed")
        node_extract = temp / "node"
        with ZipFile(node_archive) as zip_file:
            zip_file.extractall(node_extract)
        node_root = _single_extracted_root(node_extract)
        bundled_node = node_root / "node.exe"
        npm = node_root / "npm.cmd"
        if not bundled_node.is_file() or not npm.is_file():
            raise RuntimeError("Node.js runtime is incomplete")

        source_archive = temp / f"omniroute-{OMNIROUTE_COMMIT}.zip"
        _download(OMNIROUTE_SOURCE_URL, source_archive)
        source_extract = temp / "omniroute-source"
        with ZipFile(source_archive) as zip_file:
            zip_file.extractall(source_extract)
        source_root = _single_extracted_root(source_extract)

        package_json = source_root / "package.json"
        source_entry = source_root / "bin" / "omniroute.mjs"
        if not package_json.is_file() or not source_entry.is_file():
            raise RuntimeError("Pinned OmniRoute source snapshot is incomplete")
        metadata = json.loads(package_json.read_text(encoding="utf-8"))
        if str(metadata.get("version")) != OMNIROUTE_VERSION:
            raise RuntimeError("Pinned OmniRoute source version does not match the release version")

        packed_dir = temp / "packed"
        packed_dir.mkdir()
        pack = subprocess.run(
            [
                str(npm),
                "pack",
                "--ignore-scripts",
                "--pack-destination",
                str(packed_dir),
            ],
            cwd=source_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            env={**os.environ, "NODE_ENV": "production"},
            check=False,
        )
        if pack.returncode != 0:
            raise RuntimeError(f"OmniRoute package creation failed: {(pack.stderr or pack.stdout or '').strip()[-4000:]}")
        package_name = str(metadata.get("name") or "omniroute").split("/")[-1]
        tarball = packed_dir / f"{package_name}-{OMNIROUTE_VERSION}.tgz"
        if not tarball.is_file():
            candidates = list(packed_dir.glob("*.tgz"))
            if len(candidates) != 1:
                raise RuntimeError("OmniRoute package archive was not produced as expected")
            tarball = candidates[0]

        staging = temp / "omniroute_runtime"
        staging.mkdir(parents=True)
        (staging / "package.json").write_text(
            json.dumps(
                {
                    "name": "jarvis-omniroute-runtime-builder",
                    "private": True,
                    "version": "1.0.0",
                    "allowScripts": {
                        "file:../packed/omniroute-3.8.50.tgz": True,
                        "better-sqlite3": True,
                        "wreq-js": True,
                        "tls-client-node": True,
                        "onnxruntime-node": True,
                        "@parcel/watcher": True,
                        "@swc/core": True,
                        "koffi": True,
                        "keytar": True,
                        "esbuild": True,
                        "protobufjs": True,
                        "sharp": True,
                        "unrs-resolver": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                str(npm),
                "install",
                "--prefix",
                str(staging),
                "--no-fund",
                "--no-audit",
                "--omit=dev",
                # Keep dependencies hoisted so platform-correct native modules
                # land in staging/node_modules and can be copied into OmniRoute's
                # standalone dist payload deterministically.
                "--install-strategy=hoisted",
                "--package-lock=false",
                "--ignore-scripts=false",
                "--prefer-offline",
                "--fetch-retries=2",
                "--legacy-peer-deps",
                "--no-bin-links",
                "--no-progress",
                str(tarball),
            ],
            stdin=subprocess.DEVNULL,
            stdout=None,
            stderr=None,
            timeout=1800,
            env={**os.environ, "NODE_ENV": "production"},
            check=False,
        )
        if result.returncode != 0:
            detail = "npm install returned a non-zero exit status"
            raise RuntimeError(f"OmniRoute package installation failed in the release build: {detail[-5000:]}")

        # npm 11 may suppress lifecycle scripts even with ignore-scripts=false.
        # Repair OmniRoute's standalone native payload explicitly from the
        # platform-correct nested dependency install instead of assuming npm
        # executed the package postinstall.
        shutil.copy2(bundled_node, staging / "node.exe")
        package_root = staging / "node_modules" / "omniroute"
        root_native_candidates = [
            staging / "node_modules" / "better-sqlite3" / "build" / "Release" / "better_sqlite3.node",
            package_root / "node_modules" / "better-sqlite3" / "build" / "Release" / "better_sqlite3.node",
        ]
        app_native = package_root / "dist" / "node_modules" / "better-sqlite3" / "build" / "Release" / "better_sqlite3.node"
        root_native = next((path for path in root_native_candidates if path.is_file()), None)
        if root_native is not None:
            app_native.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root_native, app_native)
        critical_native = [
            app_native,
            package_root / "node_modules" / "wreq-js",
        ]
        if not critical_native[0].is_file():
            searched = ", ".join(str(path) for path in root_native_candidates)
            raise RuntimeError(
                "Prepared OmniRoute runtime is missing its repaired Windows better-sqlite3 binary; " + searched
            )
        if not _native_load_ok(bundled_node, critical_native[0]):
            raise RuntimeError(
                "Prepared OmniRoute better-sqlite3 binary could not be loaded"
            )

        installed_entry = staging / "node_modules" / "omniroute" / "bin" / "omniroute.mjs"
        if not installed_entry.is_file():
            raise RuntimeError("Installed OmniRoute runtime is missing its CLI entrypoint")

        check = subprocess.run(
            [
                str(staging / "node.exe"),
                str(installed_entry),
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
            raise RuntimeError(
                f"Installed OmniRoute version did not match {OMNIROUTE_VERSION}: "
                f"{(check.stdout or check.stderr or '').strip()[-1000:]}"
            )

        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(staging, destination)
        manifest = destination / "runtime-manifest.txt"
        manifest.write_text(
            f"schema={RUNTIME_CACHE_SCHEMA}\n"
            f"node={NODE_VERSION}\nomniroute={OMNIROUTE_VERSION}\n"
            f"commit={OMNIROUTE_COMMIT}\n",
            encoding="utf-8",
        )


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    destination = Path(args[0]) if args else Path("build_vendor/omniroute_runtime")
    prepare(destination)
    print(f"Prepared Node {NODE_VERSION} + OmniRoute {OMNIROUTE_VERSION} ({OMNIROUTE_COMMIT}) at {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
