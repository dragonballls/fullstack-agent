"""Command-line entry point for Jarvis readiness diagnostics."""

from __future__ import annotations

import sys

from quality_of_life.readiness import check_readiness, format_report


def main() -> int:
    report = check_readiness()
    print(format_report(report))
    return 0 if report.ready else 1


if __name__ == "__main__":
    sys.exit(main())
