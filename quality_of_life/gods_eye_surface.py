"""Embedded God’s Eye desktop surface using optional pywebview."""

from __future__ import annotations

import html
import json
from typing import Any

from .gods_eye_map import MapView


class GodsEyeSurfaceUnavailable(RuntimeError):
    pass


class GodsEyeSurface:
    """Render God’s Eye state into a self-contained desktop window."""

    def __init__(self, webview_module: Any | None = None) -> None:
        self.webview = webview_module

    @staticmethod
    def html_for(view: MapView) -> str:
        payload = json.dumps(view.as_dict(), separators=(",", ":"), ensure_ascii=True)
        center = view.center
        markers = []
        for place in view.markers:
            label = html.escape(place.name, quote=True)
            markers.append(
                "L.marker([%s,%s]).addTo(map).bindPopup(%s);"
                % (place.point.latitude, place.point.longitude, json.dumps(label))
            )
        markers_js = "".join(markers)
        return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>God's Eye</title>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>
<style>
html,body,#map{{height:100%;margin:0;background:#070b12}}#status{{position:fixed;z-index:1000;top:12px;left:12px;padding:8px 12px;border-radius:8px;background:rgba(7,11,18,.88);color:#fff;font:14px system-ui,sans-serif}}
</style>
</head>
<body>
<div id='status'>God’s Eye</div><div id='map'></div>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
<script>
const state = {payload};
const map = L.map('map').setView([{center.latitude},{center.longitude}], {view.zoom});
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'}}).addTo(map);
{markers_js}
window.GODS_EYE_STATE = state;
</script>
</body>
</html>"""

    def show(self, view: MapView, *, title: str = "God’s Eye") -> None:
        if self.webview is None:
            try:
                import webview  # type: ignore
            except ImportError as exc:
                raise GodsEyeSurfaceUnavailable("Install quality_of_life optional GUI dependencies to open the God’s Eye window.") from exc
            self.webview = webview
        page = self.html_for(view)
        try:
            self.webview.create_window(title, html=page, width=1400, height=900, min_size=(900, 600))
            self.webview.start()
        except Exception as exc:
            raise GodsEyeSurfaceUnavailable(f"Unable to open the God’s Eye window: {exc}") from exc
