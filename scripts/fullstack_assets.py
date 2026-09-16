"""Runtime resource resolution for the embedded Fullstack Agent assets."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def bundle_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    configured = os.environ.get("JARVIS_BUNDLE_ROOT")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "build_vendor"


def embedded_path(relative: str) -> Path:
    path = (bundle_root() / relative).resolve()
    root = bundle_root().resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"resource escapes bundle root: {relative}")
    if not path.exists():
        raise FileNotFoundError(path)
    return path
