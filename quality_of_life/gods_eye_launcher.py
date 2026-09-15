"""Launch the isolated God’s Eye GUI without blocking the main Jarvis process."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence


class GodsEyeLauncher:
    """Start the God’s Eye window as a child Python process with shell execution disabled."""

    def __init__(self, popen=subprocess.Popen) -> None:
        self._popen = popen

    def launch_query(self, query: str) -> None:
        query = query.strip()
        if not query:
            raise ValueError("location query cannot be empty")
        argv: Sequence[str] = (sys.executable, "-m", "quality_of_life.gods_eye_window", "--query", query)
        self._popen(argv, shell=False, close_fds=True)
