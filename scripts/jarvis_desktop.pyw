"""Windows no-console entrypoint for the complete Jarvis desktop host."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.jarvis_desktop_extensions import (  # noqa: E402
    JarvisExtendedController,
    is_family_window_request,
    run_family_window,
)
from scripts.jarvis_desktop import FullstackJarvisHost  # noqa: E402


def main() -> int:
    if is_family_window_request():
        return run_family_window()
    controller = JarvisExtendedController()
    host = FullstackJarvisHost(controller)
    try:
        host.start()
        host.run_window()
        return 0
    except Exception:
        try:
            from scripts.jarvis_desktop import LOGGER
            LOGGER.exception("Jarvis extended desktop host failed to start")
        except Exception:
            pass
        return 1
    finally:
        host.stop()


if __name__ == "__main__":
    raise SystemExit(main())
