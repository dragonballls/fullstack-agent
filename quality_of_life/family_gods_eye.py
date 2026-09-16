"""God’s Eye family-location surface for authorized provider data."""

from __future__ import annotations

import html
import json
import threading
from typing import Any

from .family_locations import FamilyLocationService


class FamilyGodsEyeSurface:
    """Render family locations and live-follow state in an isolated map window."""

    def __init__(self, service: FamilyLocationService, webview_module: Any | None = None) -> None:
        self.service = service
        self.webview = webview_module
        self._window: Any | None = None

    def _state(self) -> dict[str, object]:
        try:
            self.service.refresh()
        except Exception:
            pass
        return self.service.map_state()

    class Api:
        def __init__(self, owner: "FamilyGodsEyeSurface") -> None:
            self.owner = owner

        def state(self) -> dict[str, object]:
            return self.owner._state()

        def stop_follow(self) -> bool:
            self.owner.service.stop_follow()
            return True

    @staticmethod
    def html_for(initial: dict[str, object]) -> str:
        payload = json.dumps(initial, ensure_ascii=True, separators=(",", ":"))
        safe = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        return f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>God's Eye — Family</title>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>
<style>
html,body,#map{{height:100%;margin:0;background:#070b12}}#status{{position:fixed;z-index:1000;top:12px;left:12px;padding:9px 12px;border-radius:8px;background:rgba(7,11,18,.9);color:#fff;font:14px system-ui,sans-serif}}#stop{{position:fixed;z-index:1000;top:58px;left:12px;padding:9px 12px;border:0;border-radius:8px;background:#fff;color:#111;cursor:pointer}}
</style></head><body>
<div id='status'>God’s Eye — Family</div><button id='stop'>Stop following</button><div id='map'></div>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
<script>
let state={safe};
let map=L.map('map');
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}}).addTo(map);
let markers=new Map();
function render(s){{
  state=s;
  const items=Array.isArray(s.family_markers)?s.family_markers:[];
  const bounds=[];
  for(const [id,m] of Object.entries(Object.fromEntries(items.map(x=>[x.member_id,x])))){{
    const p=[m.latitude,m.longitude]; bounds.push(p);
    let marker=markers.get(id);
    if(!marker){{ marker=L.marker(p).addTo(map); markers.set(id,marker); }} else marker.setLatLng(p);
    const freshness=m.available?(m.stale?'stale':'updated'):'sharing paused';
    marker.bindPopup('<b>'+String(m.name)+'</b><br>'+freshness+'<br>Updated: '+String(m.observed_at));
  }}
  if(s.follow_center){{ map.setView([s.follow_center.latitude,s.follow_center.longitude],15); }}
  else if(bounds.length){{ map.fitBounds(bounds,{{padding:[50,50]}}); }}
  document.getElementById('status').textContent=s.follow_member_id?'Following family member':'Family locations';
}}
render(state);
document.getElementById('stop').onclick=()=>window.pywebview.api.stop_follow().then(()=>window.pywebview.api.state()).then(render);
window.addEventListener('pywebviewready',()=>{{ window.pywebview.api.state().then(render); setInterval(()=>window.pywebview.api.state().then(render),5000); }});
</script></body></html>"""

    def show(self, focus_member_id: str | None = None) -> int:
        initial = self._state()
        if focus_member_id:
            try:
                self.service.follow(focus_member_id)
                initial = self.service.map_state()
            except Exception:
                pass
        if self.webview is None:
            try:
                import webview  # type: ignore
            except ImportError as exc:
                raise RuntimeError("pywebview is required for the family God’s Eye window") from exc
            self.webview = webview
        api = self.Api(self)
        self._window = self.webview.create_window(
            "God’s Eye — Family",
            html=self.html_for(initial),
            js_api=api,
            width=1400,
            height=900,
            min_size=(900, 600),
        )
        self.webview.start()
        return 0
