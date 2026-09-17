"""Advanced persistent Jarvis workspace UI bridge.

The module is intentionally independent from the native host so the UI contract can
be tested without pywebview or Windows. The native entrypoint installs the bridge
before creating the window, preserving the existing visualizer/voice stack.
"""

from __future__ import annotations

from typing import Any

from .permissions import Capability
from .workspace import WorkspaceState, WorkspaceType


class WorkspaceBridge:
    """Stateful, deterministic workspace controller exposed to the web UI."""

    def __init__(self) -> None:
        self._state = WorkspaceState.default()

    def workspace_state(self) -> dict[str, object]:
        return self._state.as_dict()

    def activate(self, workspace: str) -> dict[str, object]:
        try:
            target = WorkspaceType(workspace)
        except ValueError as exc:
            raise ValueError(f"unknown workspace: {workspace}") from exc
        self._state = self._state.activate(target)
        return self._state.as_dict()


def install(desktop_module: Any) -> None:
    """Install workspace API and script into the existing desktop host."""
    base_api = desktop_module.JarvisWebApi

    class WorkspaceWebApi(base_api, WorkspaceBridge):
        def __init__(self, host: Any) -> None:
            base_api.__init__(self, host)
            WorkspaceBridge.__init__(self)

        def workspace_state(self) -> dict[str, object]:
            return WorkspaceBridge.workspace_state(self)

        def activate_workspace(self, workspace: str) -> dict[str, object]:
            return WorkspaceBridge.activate(self, workspace)

        def gods_eye_status(self) -> dict[str, object]:
            """Return a safe UI status without inventing a location."""
            try:
                runtime = self.host.controller.runtime
                result = runtime.dispatch(Capability.LOCATION_READ, "locations.current")
                return {"ok": True, "location": result}
            except Exception as exc:
                return {
                    "ok": False,
                    "available": False,
                    "reason": f"Location provider unavailable: {type(exc).__name__}",
                }

    desktop_module.JarvisWebApi = WorkspaceWebApi
    desktop_module.TEXT_INPUT_SCRIPT += "\n" + workspace_script()


def workspace_script() -> str:
    return r'''(() => {
  "use strict";
  if (window.__jarvisWorkspaceInstalled) return;
  window.__jarvisWorkspaceInstalled = true;

  const style = document.createElement("style");
  style.id = "jarvis-workspace-style";
  style.textContent = `
    #jarvis-workspace-shell { position:fixed; inset:0; z-index:2147483000; pointer-events:none; color:#e8f4ef; font-family:Inter,Segoe UI,system-ui,sans-serif; }
    #jarvis-workspace-top { position:absolute; left:18px; right:18px; top:16px; height:46px; display:flex; align-items:center; gap:8px; pointer-events:auto; }
    .jw-brand { display:flex; align-items:center; gap:9px; margin-right:8px; padding:9px 13px; border:1px solid rgba(143,232,184,.14); border-radius:12px; background:rgba(2,8,6,.58); backdrop-filter:blur(12px); letter-spacing:.22em; font-size:10px; }
    .jw-pulse { width:8px; height:8px; border-radius:50%; background:#59e69b; box-shadow:0 0 16px rgba(89,230,155,.8); }
    .jw-tab { border:1px solid rgba(143,232,184,.11); border-radius:10px; padding:9px 11px; color:#819a91; background:rgba(2,8,6,.44); cursor:pointer; font-size:10px; letter-spacing:.12em; transition:.18s ease; }
    .jw-tab:hover,.jw-tab.active { color:#dfffee; border-color:rgba(143,232,184,.42); background:rgba(61,220,132,.08); box-shadow:0 0 18px rgba(61,220,132,.08); }
    #jarvis-workspace-content { position:absolute; inset:76px 18px 112px; pointer-events:none; }
    .jw-view { display:none; position:absolute; inset:0; pointer-events:auto; }
    .jw-view.active { display:block; }
    .jw-grid { display:grid; grid-template-columns:minmax(0,1fr) 300px; grid-template-rows:minmax(0,1fr) 130px; gap:12px; height:100%; }
    .jw-card { border:1px solid rgba(143,232,184,.12); border-radius:16px; background:linear-gradient(145deg,rgba(4,13,10,.76),rgba(2,7,6,.54)); backdrop-filter:blur(12px); box-shadow:inset 0 1px rgba(255,255,255,.025),0 14px 40px rgba(0,0,0,.18); overflow:hidden; }
    .jw-card-title { padding:12px 14px 8px; font-size:9px; letter-spacing:.22em; color:#78958a; }
    .jw-map { position:relative; height:calc(100% - 30px); overflow:hidden; background:radial-gradient(circle at 52% 44%,rgba(61,220,132,.09),transparent 26%),linear-gradient(140deg,#06100d,#020705 58%,#07120e); }
    .jw-map::before { content:""; position:absolute; inset:0; opacity:.23; background-image:linear-gradient(rgba(143,232,184,.10) 1px,transparent 1px),linear-gradient(90deg,rgba(143,232,184,.10) 1px,transparent 1px); background-size:46px 46px; transform:perspective(700px) rotateX(55deg) scale(1.4); transform-origin:center bottom; }
    .jw-radar { position:absolute; left:50%; top:50%; width:170px; height:170px; transform:translate(-50%,-50%); border:1px solid rgba(89,230,155,.28); border-radius:50%; box-shadow:0 0 0 35px rgba(89,230,155,.025),0 0 0 70px rgba(89,230,155,.018); }
    .jw-radar::after { content:""; position:absolute; left:50%; top:50%; width:1px; height:50%; transform-origin:bottom; background:linear-gradient(transparent,#59e69b); animation:jw-scan 3.4s linear infinite; }
    @keyframes jw-scan { to { transform:rotate(360deg); } }
    .jw-marker { position:absolute; width:12px; height:12px; border-radius:50%; background:#72f2ad; box-shadow:0 0 16px rgba(114,242,173,.8); border:2px solid rgba(255,255,255,.7); transform:translate(-50%,-50%); }
    .jw-marker span { position:absolute; top:16px; left:9px; white-space:nowrap; font-size:9px; color:#a9c8bb; }
    .jw-empty { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; flex-direction:column; gap:7px; color:#61766e; font-size:10px; letter-spacing:.13em; text-align:center; }
    .jw-empty strong { color:#9dbab0; font-size:12px; }
    .jw-list { padding:4px 12px 12px; display:flex; flex-direction:column; gap:7px; overflow:auto; height:calc(100% - 32px); }
    .jw-row { display:flex; justify-content:space-between; gap:10px; padding:10px; border:1px solid rgba(143,232,184,.09); border-radius:10px; background:rgba(255,255,255,.018); font-size:10px; }
    .jw-row b { color:#bfe0d3; font-weight:500; }
    .jw-row small { color:#617a70; }
    .jw-bottom { grid-column:1 / -1; display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; }
    .jw-stat { padding:13px; }
    .jw-stat strong { display:block; font-size:18px; color:#dfffee; margin-top:5px; }
    .jw-stat small { color:#668077; font-size:9px; letter-spacing:.12em; }
    .jw-center { height:100%; display:flex; align-items:center; justify-content:center; }
    .jw-home-card { width:min(760px,90%); padding:30px; text-align:left; }
    .jw-home-card h1 { margin:0 0 8px; font-size:28px; font-weight:500; letter-spacing:.04em; }
    .jw-home-card p { color:#78958a; line-height:1.6; font-size:12px; max-width:640px; }
    .jw-command-hint { display:flex; flex-wrap:wrap; gap:7px; margin-top:18px; }
    .jw-chip { padding:8px 10px; border-radius:9px; border:1px solid rgba(143,232,184,.10); color:#86a499; background:rgba(255,255,255,.02); font-size:9px; cursor:pointer; }
    .jw-chip:hover { color:#dfffee; border-color:rgba(143,232,184,.34); }
    @media(max-width:900px){ #jarvis-workspace-top{overflow:auto;} .jw-grid{grid-template-columns:1fr;} .jw-bottom{display:none;} .jw-grid>.jw-card:nth-child(2){display:none;} }
  `;
  document.head.appendChild(style);

  const shell = document.createElement("div");
  shell.id = "jarvis-workspace-shell";
  shell.innerHTML = `
    <div id="jarvis-workspace-top">
      <div class="jw-brand"><span class="jw-pulse"></span>JARVIS</div>
      <button class="jw-tab active" data-workspace="home">HOME</button>
      <button class="jw-tab" data-workspace="gods-eye">GOD'S EYE</button>
      <button class="jw-tab" data-workspace="coding">CODING</button>
      <button class="jw-tab" data-workspace="browser">BROWSER</button>
      <button class="jw-tab" data-workspace="system">SYSTEM</button>
      <button class="jw-tab" data-workspace="workflows">WORKFLOWS</button>
    </div>
    <div id="jarvis-workspace-content">
      <section class="jw-view active" data-view="home"><div class="jw-center"><div class="jw-card jw-home-card"><div class="jw-card-title">ACTIVE AGENT SHELL</div><h1>Jarvis is ready.</h1><p>The command surface stays available while Jarvis changes workspaces. You can type commands without leaving the active system view.</p><div class="jw-command-hint"><button class="jw-chip" data-command="Open God's Eye">OPEN GOD'S EYE</button><button class="jw-chip" data-command="Show my phone">SHOW MY PHONE</button><button class="jw-chip" data-command="Show my workflows">WORKFLOWS</button><button class="jw-chip" data-command="Check system status">SYSTEM STATUS</button></div></div></div></section>
      <section class="jw-view" data-view="gods-eye"><div class="jw-grid"><div class="jw-card"><div class="jw-card-title">GOD'S EYE / LIVE CONTEXT</div><div class="jw-map"><div class="jw-radar"></div><div class="jw-empty" id="jw-location-empty"><strong>AWAITING AUTHORIZED LOCATION DATA</strong><span>Jarvis will never invent a device or family location.</span></div></div></div><div class="jw-card"><div class="jw-card-title">ENTITIES</div><div class="jw-list" id="jw-entities"><div class="jw-row"><b>Location service</b><small>checking…</small></div><div class="jw-row"><b>Phone</b><small>not connected</small></div><div class="jw-row"><b>Family</b><small>no shared feed</small></div></div></div><div class="jw-bottom"><div class="jw-card jw-stat"><small>WORKSPACE</small><strong>GOD'S EYE</strong></div><div class="jw-card jw-stat"><small>COMMAND LINK</small><strong>ONLINE</strong></div><div class="jw-card jw-stat"><small>LOCATION PRIVACY</small><strong>GUARDED</strong></div></div></div></section>
      <section class="jw-view" data-view="coding"><div class="jw-center"><div class="jw-card jw-home-card"><div class="jw-card-title">CODING AGENT</div><h1>Build • Test • Verify</h1><p>Jarvis keeps the command link alive while coding tasks run. Progress, tool activity, and failures can be surfaced here without replacing the underlying agent.</p></div></div></section>
      <section class="jw-view" data-view="browser"><div class="jw-center"><div class="jw-card jw-home-card"><div class="jw-card-title">BROWSER WORKSPACE</div><h1>Research and action</h1><p>Browser tasks can remain visible while the command bar stays available for follow-up instructions.</p></div></div></section>
      <section class="jw-view" data-view="system"><div class="jw-center"><div class="jw-card jw-home-card"><div class="jw-card-title">SYSTEM HEALTH</div><h1>Observe before changing</h1><p>System maintenance should surface resource state, active applications, and proposed changes before mutating anything.</p></div></div></section>
      <section class="jw-view" data-view="workflows"><div class="jw-center"><div class="jw-card jw-home-card"><div class="jw-card-title">WORKFLOW ENGINE</div><h1>Queued agent work</h1><p>Long-running tasks belong in workflows with progress, cancellation, and recovery instead of disappearing behind a busy screen.</p></div></div></section>
    </div>
  `;
  document.body.appendChild(shell);

  const views = [...shell.querySelectorAll(".jw-view")];
  const tabs = [...shell.querySelectorAll(".jw-tab")];
  const api = () => window.pywebview && window.pywebview.api;
  const storageKey = "jarvis.activeWorkspace";

  function setView(name, persist = true) {
    views.forEach(v => v.classList.toggle("active", v.dataset.view === name));
    tabs.forEach(t => t.classList.toggle("active", t.dataset.workspace === name));
    if (persist) {
      try { window.localStorage.setItem(storageKey, name); } catch (_) {}
    }
    if (api() && api().activate_workspace) api().activate_workspace(name).catch(() => {});
    if (name === "gods-eye" && api() && api().gods_eye_status) refreshLocation();
  }

  async function refreshLocation() {
    const empty = document.getElementById("jw-location-empty");
    const entities = document.getElementById("jw-entities");
    try {
      const result = await api().gods_eye_status();
      if (result && result.ok && result.location) {
        empty.innerHTML = "<strong>LOCATION DATA AVAILABLE</strong><span>Source and permission state received from Jarvis.</span>";
        entities.innerHTML = '<div class="jw-row"><b>Location service</b><small>authorized</small></div><div class="jw-row"><b>Current location</b><small>available</small></div><div class="jw-row"><b>Phone / family</b><small>separate provider</small></div>';
      } else if (result && result.reason) {
        empty.innerHTML = `<strong>LOCATION FEED OFFLINE</strong><span>${String(result.reason).replace(/[<>]/g, "")}</span>`;
      }
    } catch (_) {
      empty.innerHTML = "<strong>LOCATION FEED OFFLINE</strong><span>The workspace remains available while the provider is unavailable.</span>";
    }
  }

  tabs.forEach(tab => tab.addEventListener("click", () => setView(tab.dataset.workspace)));
  shell.querySelectorAll(".jw-chip").forEach(chip => chip.addEventListener("click", () => {
    const input = document.getElementById("jarvis-text-input");
    if (input) { input.value = chip.dataset.command || ""; input.focus(); }
  }));

  window.jarvisWorkspaceState = { setView, refreshLocation };
  let restored = "home";
  try {
    const candidate = window.localStorage.getItem(storageKey);
    if (["home", "gods-eye", "coding", "browser", "system", "workflows"].includes(candidate)) restored = candidate;
  } catch (_) {}
  setView(restored, false);
  if (api() && api().workspace_state) api().workspace_state().then(state => {
    if (!window.localStorage.getItem(storageKey) && state && state.active) setView(state.active, false);
  }).catch(() => {});
})();
'''