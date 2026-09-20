"""Build the pinned, self-contained OmniRoute runtime used by Jarvis.exe.

OmniRoute 3.8.50 is the current official published Windows release,
so the release bundle is sourced from its exact immutable commit instead of
assuming the version already exists on npm. The resulting local package is
installed with production dependencies and verified before packaging.
"""

from __future__ import annotations

import base64
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
OMNIROUTE_NPM_METADATA_URL = f"https://registry.npmjs.org/omniroute/{OMNIROUTE_VERSION}"
RUNTIME_CACHE_SCHEMA = "7"


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
            env={**os.environ, "NODE_ENV": "production", "CI": "1", "OMNIROUTE_SKIP_POSTINSTALL": "1"},
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and "native-ok" in (result.stdout or "")


def _runtime_is_healthy(destination: Path) -> bool:
    node = destination / "node.exe"
    entry = destination / "node_modules" / "omniroute" / "bin" / "omniroute.mjs"
    native_candidates = [
        destination
        / "node_modules"
        / "omniroute"
        / "dist"
        / "node_modules"
        / "better-sqlite3"
        / "prebuilds"
        / "win32-x64.node",
        destination
        / "node_modules"
        / "omniroute"
        / "dist"
        / "node_modules"
        / "better-sqlite3"
        / "build"
        / "Release"
        / "better_sqlite3.node",
    ]
    native = next((path for path in native_candidates if path.is_file()), None)
    if native is None or not _native_load_ok(node, native) or not entry.is_file():
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

        metadata_path = temp / "omniroute-npm-metadata.json"
        _download(OMNIROUTE_NPM_METADATA_URL, metadata_path)
        registry = json.loads(metadata_path.read_text(encoding="utf-8"))
        registry_version = str(registry.get("version") or "")
        registry_git_head = str(registry.get("gitHead") or "")
        dist = registry.get("dist") or {}
        tarball_url = str(dist.get("tarball") or "")
        integrity = str(dist.get("integrity") or "")
        if registry_version != OMNIROUTE_VERSION:
            raise RuntimeError(
                f"npm registry returned OmniRoute {registry_version}, expected {OMNIROUTE_VERSION}"
            )
        if registry_git_head and registry_git_head != OMNIROUTE_COMMIT:
            raise RuntimeError(
                "npm registry gitHead does not match pinned OmniRoute commit: "
                f"{registry_git_head} != {OMNIROUTE_COMMIT}"
            )
        if not tarball_url or not integrity.startswith("sha512-"):
            raise RuntimeError("npm registry did not provide a verifiable OmniRoute tarball")
        tarball = temp / f"omniroute-{OMNIROUTE_VERSION}.tgz"
        _download(tarball_url, tarball)
        expected_sha512 = base64.b64decode(integrity.removeprefix("sha512-"))
        actual_sha512 = hashlib.sha512(tarball.read_bytes()).digest()
        if actual_sha512 != expected_sha512:
            raise RuntimeError("OmniRoute npm tarball integrity verification failed")

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
            env={**os.environ, "NODE_ENV": "production", "CI": "1", "OMNIROUTE_SKIP_POSTINSTALL": "1"},
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
        native_candidates = [
            (
                staging / "node_modules" / "better-sqlite3" / "prebuilds" / "win32-x64.node",
                package_root / "dist" / "node_modules" / "better-sqlite3" / "prebuilds" / "win32-x64.node",
            ),
            (
                staging / "node_modules" / "better-sqlite3" / "build" / "Release" / "better_sqlite3.node",
                package_root / "dist" / "node_modules" / "better-sqlite3" / "build" / "Release" / "better_sqlite3.node",
            ),
            (
                package_root / "node_modules" / "better-sqlite3" / "prebuilds" / "win32-x64.node",
                package_root / "dist" / "node_modules" / "better-sqlite3" / "prebuilds" / "win32-x64.node",
            ),
            (
                package_root / "node_modules" / "better-sqlite3" / "build" / "Release" / "better_sqlite3.node",
                package_root / "dist" / "node_modules" / "better-sqlite3" / "build" / "Release" / "better_sqlite3.node",
            ),
        ]
        native_pair = next(((source, target) for source, target in native_candidates if source.is_file()), None)
        if native_pair is None:
            searched = ", ".join(str(source) for source, _ in native_candidates)
            raise RuntimeError(
                "Prepared OmniRoute runtime is missing a usable Windows better-sqlite3 native binary; " + searched
            )
        source_native, app_native = native_pair
        app_native.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_native, app_native)
        if not _native_load_ok(bundled_node, app_native):
            raise RuntimeError(
                "Prepared OmniRoute better-sqlite3 binary could not be loaded"
            )

        installed_package = staging / "node_modules" / "omniroute"
        installed_entry = installed_package / "bin" / "omniroute.mjs"
        installed_server = installed_package / "dist" / "server.js"
        if not installed_entry.is_file():
            raise RuntimeError("Installed OmniRoute runtime is missing its CLI entrypoint")
        if not installed_server.is_file():
            raise RuntimeError(
                "Installed OmniRoute npm package is missing dist/server.js; "
                "the published runtime bundle is incomplete"
            )

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
