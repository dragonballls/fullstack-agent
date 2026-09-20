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


def main() -> int:
    # Start the lightweight embedded visualizer before importing the optional,
    # heavy UI/neural layers. This gives a frozen one-file EXE a responsive
    # health endpoint during cold extraction/import and avoids the previous
    # 120-second smoke timeout while keeping those layers intact.
    visualizer = _desktop.VisualizerAdapter()
    try:
        visualizer.start()
        from quality_of_life.workspace_ui import install as install_workspace_ui
        from quality_of_life.ui_builds import install as install_ui_builds
        from quality_of_life.neural_world import install as install_neural_world
        install_workspace_ui(_desktop)
        install_ui_builds(_desktop)
        install_neural_world(_desktop)
        return _desktop.main(prestarted_visualizer=visualizer)
    except Exception:
        try:
            visualizer.stop()
        except Exception:
            _desktop.LOGGER.exception("prestarted visualizer failed during frozen bootstrap cleanup")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
