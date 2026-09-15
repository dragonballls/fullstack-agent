"""CLI entrypoint used to open a God’s Eye place inside its own desktop window."""

from __future__ import annotations

import argparse

from .gods_eye import GeoPoint, Place
from .gods_eye_map import GodsEyeMap
from .gods_eye_surface import GodsEyeSurface
from .location import NominatimGeocoder


def main() -> int:
    parser = argparse.ArgumentParser(description="Open a place in the God’s Eye desktop surface")
    parser.add_argument("--query", required=True)
    args = parser.parse_args()
    results = NominatimGeocoder().search(args.query)
    if not results:
        raise SystemExit(f"No location found for: {args.query}")
    GodsEyeSurface().show(GodsEyeMap.build_search_view(results, selected=results[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
