"""Windows no-console entrypoint for the Jarvis desktop host."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.jarvis_runtime_resilience import install_desktop_resilience  # noqa: E402

install_desktop_resilience()

from scripts.jarvis_desktop import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
