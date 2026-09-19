"""Repository-wide quality floor and monotonic quality-ladder enforcement.

The quality floor is intentionally one-way: the minimum verified contract may stay
the same or become stricter, but CI/self-coding rejects attempts to weaken it.
UI quality is described by explicit rungs rather than subjective visual scores.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any, Mapping


UI_QUALITY_LADDER: dict[int, str] = {
    1: "Foundation",
    2: "Protected",
    3: "Integrated",
    4: "Verified",
    5: "Scale",
}

DEFAULT_QUALITY_FLOOR: dict[str, Any] = {
    "schema_version": 1,
    "product_quality_level": 4,
    "ui_minimum_level": 4,
    "required_protected_ui_builds": 4,
    "performance": {
        "max_ui_build_bytes": 350_000,
        "max_ui_manager_script_bytes": 50_000,
    },
    "required_files": [
        "quality_of_life/ui_builds.py",
        "quality_of_life/runtime.py",
        "self_coding/agent.py",
        "scripts/jarvis_desktop.py",
        ".github/workflows/jarvis-release-gate.yml",
        "tests/test_ui_builds.py",
        "tests/test_self_coding.py",
        "tests/test_qol_runtime.py",
    ],
    "required_tokens": {
        "quality_of_life/ui_builds.py": [
            "class UIBuildStore",
            "def activate",
            "def rollback",
            "def build_manager_script",
            "quality_level",
        ],
        "quality_of_life/runtime.py": [
            "self_coding.approve",
            "self_coding.undo",
        ],
        "self_coding/agent.py": [
            "Direct main publication is disabled",
            "System-coherence mandate",
            "approve_checkpoint",
            "undo_checkpoint",
        ],
        ".github/workflows/jarvis-release-gate.yml": [
            "Native Windows Jarvis.exe",
            "Smoke-test the packaged native Jarvis host",
        ],
        "tests/test_ui_builds.py": [
            "test_protected_builds_cannot_be_overwritten_or_deleted",
            "test_manager_script_is_valid_javascript_when_node_is_available",
        ],
        "tests/test_self_coding.py": [
            "test_direct_main_publication_is_disabled",
            "test_self_coding_prompt_requires_repository_wide_coherence",
        ],
    },
}


class QualityFloorError(RuntimeError):
    """Raised when a repository would fall below its previously verified floor."""


def _json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise QualityFloorError(f"Unable to read quality floor manifest: {path}") from exc
    if not isinstance(payload, dict):
        raise QualityFloorError("Quality floor manifest must contain a JSON object.")
    return payload


def load_floor(root: str | Path) -> dict[str, Any]:
    path = Path(root) / "quality_floor.json"
    if not path.is_file():
        raise QualityFloorError("quality_floor.json is missing.")
    payload = _json(path)
    merged = dict(DEFAULT_QUALITY_FLOOR)
    merged["performance"] = dict(DEFAULT_QUALITY_FLOOR["performance"])
    merged["required_tokens"] = {
        key: list(value) for key, value in DEFAULT_QUALITY_FLOOR["required_tokens"].items()
    }
    for key, value in payload.items():
        if key == "performance":
            if not isinstance(value, Mapping):
                raise QualityFloorError("quality floor performance section must be an object.")
            merged["performance"].update(value)
        elif key == "required_tokens":
            if not isinstance(value, Mapping):
                raise QualityFloorError("quality floor required_tokens section must be an object.")
            merged["required_tokens"] = {
                str(file): [str(token) for token in tokens]
                for file, tokens in value.items()
            }
        elif key == "required_files":
            merged["required_files"] = [str(item) for item in value]
        else:
            merged[key] = value

    if int(merged["schema_version"]) < 1:
        raise QualityFloorError("quality floor schema_version must be >= 1.")
    if int(merged["product_quality_level"]) not in UI_QUALITY_LADDER:
        raise QualityFloorError("product_quality_level is outside the UI quality ladder.")
    if int(merged["ui_minimum_level"]) not in UI_QUALITY_LADDER:
        raise QualityFloorError("ui_minimum_level is outside the UI quality ladder.")
    if int(merged["ui_minimum_level"]) > int(merged["product_quality_level"]):
        raise QualityFloorError("ui_minimum_level cannot exceed product_quality_level.")
    if int(merged["required_protected_ui_builds"]) < 1:
        raise QualityFloorError("required_protected_ui_builds must be positive.")
    for field in ("max_ui_build_bytes", "max_ui_manager_script_bytes"):
        if int(merged["performance"][field]) <= 0:
            raise QualityFloorError(f"{field} must be positive.")
    return merged


def _git_show(root: Path, ref: str, path: str) -> dict[str, Any] | None:
    result = subprocess.run(
        ("git", "show", f"{ref}:{path}"),
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise QualityFloorError(f"Baseline quality floor is invalid at {ref}:{path}") from exc
    if not isinstance(payload, dict):
        raise QualityFloorError(f"Baseline quality floor is not a JSON object at {ref}:{path}")
    return payload


def _normalized_manifest(payload: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULT_QUALITY_FLOOR)
    merged["performance"] = dict(DEFAULT_QUALITY_FLOOR["performance"])
    merged["required_tokens"] = {
        key: list(value) for key, value in DEFAULT_QUALITY_FLOOR["required_tokens"].items()
    }
    for key, value in payload.items():
        if key == "performance" and isinstance(value, Mapping):
            merged["performance"].update(value)
        elif key == "required_tokens" and isinstance(value, Mapping):
            merged["required_tokens"] = {
                str(file): [str(token) for token in tokens]
                for file, tokens in value.items()
            }
        elif key == "required_files":
            merged["required_files"] = [str(item) for item in value]
        else:
            merged[key] = value
    return merged


def compare_to_baseline(current: Mapping[str, Any], baseline: Mapping[str, Any]) -> None:
    """Reject every supported floor weakening; equal or stricter is allowed."""
    current_n = _normalized_manifest(current)
    baseline_n = _normalized_manifest(baseline)

    if int(current_n["schema_version"]) < int(baseline_n["schema_version"]):
        raise QualityFloorError("Quality-floor schema was lowered.")
    if int(current_n["product_quality_level"]) < int(baseline_n["product_quality_level"]):
        raise QualityFloorError("Product quality level was lowered.")
    if int(current_n["ui_minimum_level"]) < int(baseline_n["ui_minimum_level"]):
        raise QualityFloorError("UI minimum quality level was lowered.")
    if int(current_n["required_protected_ui_builds"]) < int(baseline_n["required_protected_ui_builds"]):
        raise QualityFloorError("Required protected UI build count was lowered.")

    for field in ("max_ui_build_bytes", "max_ui_manager_script_bytes"):
        if int(current_n["performance"][field]) > int(baseline_n["performance"][field]):
            raise QualityFloorError(f"Performance budget was weakened: {field} increased.")

    current_files = set(current_n["required_files"])
    missing_files = set(baseline_n["required_files"]) - current_files
    if missing_files:
        raise QualityFloorError(f"Required quality-floor files were removed: {sorted(missing_files)}")

    current_tokens = {
        file: set(tokens) for file, tokens in current_n["required_tokens"].items()
    }
    for file, tokens in baseline_n["required_tokens"].items():
        if not set(tokens).issubset(current_tokens.get(file, set())):
            raise QualityFloorError(f"Required quality-floor contract was weakened for {file}.")


def _verify_source_contracts(root: Path, floor: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for relative in floor["required_files"]:
        path = root / str(relative)
        if not path.is_file():
            errors.append(f"missing required file: {relative}")

    for relative, tokens in floor["required_tokens"].items():
        path = root / str(relative)
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in tokens:
            if str(token) not in text:
                errors.append(f"missing quality contract token in {relative}: {token}")
    return errors


def _verify_ui_and_performance(root: Path, floor: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        sys.path.insert(0, str(root))
        from quality_of_life.ui_builds import UIBuildStore, _BUILTIN_BUILDS, build_manager_script
    except Exception as exc:
        return [f"unable to import UI quality contract: {type(exc).__name__}: {exc}"]

    minimum_level = int(floor["ui_minimum_level"])
    expected_builtins = int(floor["required_protected_ui_builds"])
    if len(_BUILTIN_BUILDS) < expected_builtins:
        errors.append(
            f"protected UI build catalog regressed: {len(_BUILTIN_BUILDS)} < {expected_builtins}"
        )
    if any(not build.protected for build in _BUILTIN_BUILDS):
        errors.append("every shipped UI build must remain protected.")
    if any(int(build.quality_level) < minimum_level for build in _BUILTIN_BUILDS):
        errors.append("a shipped UI build is below the verified UI quality floor.")

    manager_bytes = len(build_manager_script().encode("utf-8"))
    max_manager = int(floor["performance"]["max_ui_manager_script_bytes"])
    if manager_bytes > max_manager:
        errors.append(
            f"UI build manager exceeds its performance budget: {manager_bytes} > {max_manager} bytes"
        )

    max_build = int(floor["performance"]["max_ui_build_bytes"])
    with TemporaryDirectory(prefix="jarvis-quality-floor-") as tmp:
        store = UIBuildStore(tmp)
        for build in store.list():
            size = sum(
                len(value.encode("utf-8"))
                for value in (build.css, build.markup, build.script)
            )
            if size > max_build:
                errors.append(
                    f"UI build '{build.id}' exceeds its performance budget: {size} > {max_build} bytes"
                )
            if int(build.quality_level) < minimum_level:
                errors.append(f"UI build '{build.id}' is below quality floor {minimum_level}.")
    return errors


def verify_tree(root: str | Path, baseline_ref: str | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    floor = load_floor(root)

    baseline_payload = None
    if baseline_ref:
        baseline_payload = _git_show(root, baseline_ref, "quality_floor.json")
        if baseline_payload is not None:
            compare_to_baseline(floor, baseline_payload)

    errors = _verify_source_contracts(root, floor)
    errors.extend(_verify_ui_and_performance(root, floor))
    if errors:
        raise QualityFloorError("\n".join(errors))

    return {
        "ok": True,
        "product_quality_level": int(floor["product_quality_level"]),
        "ui_minimum_level": int(floor["ui_minimum_level"]),
        "ui_minimum_name": UI_QUALITY_LADDER[int(floor["ui_minimum_level"])],
        "performance": dict(floor["performance"]),
        "baseline_checked": bool(baseline_ref and baseline_payload is not None),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Jarvis quality floor and reject regressions.")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--baseline", default="", help="Git ref to compare the quality floor against")
    args = parser.parse_args(argv)
    try:
        result = verify_tree(args.root, args.baseline or None)
    except QualityFloorError as exc:
        print(f"QUALITY FLOOR FAILED: {exc}")
        return 1
    print(
        "QUALITY FLOOR PASSED: "
        f"product=Q{result['product_quality_level']} "
        f"ui_floor=Q{result['ui_minimum_level']} ({result['ui_minimum_name']}) "
        f"baseline_checked={result['baseline_checked']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
