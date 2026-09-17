"""Windows no-console entrypoint for the Jarvis desktop host."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.jarvis_runtime_resilience import install_desktop_resilience  # noqa: E402

install_desktop_resilience()

import scripts.jarvis_desktop as _desktop  # noqa: E402
from quality_of_life.workspace_ui import install as install_workspace_ui  # noqa: E402
from quality_of_life.ui_builds import install as install_ui_builds  # noqa: E402

install_workspace_ui(_desktop)
install_ui_builds(_desktop)
main = _desktop.main


if __name__ == "__main__":
    raise SystemExit(main())
