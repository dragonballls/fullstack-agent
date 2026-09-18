"""Persistent, rollback-safe storage for unlimited Jarvis UI builds.

UI builds are presentation overlays layered on top of the existing Fullstack host.
The original visualizer and command surface remain the base UI and are never replaced
by this subsystem. Builds live in the user's local Jarvis data directory, so new
designs can be added without modifying the application binary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
from typing import Any, Mapping

from .neural_mesh import NEURAL_MESH_BUILTIN


_BUILD_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_FORBIDDEN_MARKUP = re.compile(
    r"<\s*script\b|<\s*(iframe|object|embed)\b|"
    r"\bon[a-z]+\s*=|javascript\s*:",
    re.IGNORECASE,
)
_MAX_ASSET_BYTES = 512 * 1024
_MAX_NAME_LENGTH = 120
_MAX_VERSION_LENGTH = 40
_MAX_DESCRIPTION_LENGTH = 2000
DEFAULT_BUILD_ID = "workspace-default"
MAX_ROLLBACK_HISTORY = 20


def default_store_root() -> Path:
    """Return a user-writable location that also works from a frozen executable."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "Jarvis" / "ui-builds"


@dataclass(frozen=True)
class UIBuild:
    id: str
    name: str
    version: str
    description: str = ""
    css: str = ""
    markup: str = ""
    script: str = ""
    protected: bool = False
    created_at: str = ""
    updated_at: str = ""

    def metadata(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "protected": self.protected,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def payload(self) -> dict[str, object]:
        return asdict(self)


_BUILTIN_BUILDS = (
    UIBuild(
        id=DEFAULT_BUILD_ID,
        name="Workspace Default",
        version="1.0.0",
        description="Preserves the current Fullstack visualizer, Jarvis command bar, and workspace overlay unchanged.",
        protected=True,
    ),
    UIBuild(
        id="minimal-command",
        name="Minimal Command",
        version="1.0.0",
        description="Keeps the original Fullstack visualizer and command bar while hiding the optional workspace overlay.",
        css="#jarvis-workspace-shell { display: none !important; } #jw-activity-panel { display: none !important; }",
        protected=True,
    ),
    UIBuild(
        id="status-hud",
        name="Status HUD",
        version="1.0.0",
        description="Keeps the existing UI intact and adds a lightweight non-interactive status HUD.",
        css="""
#jarvis-ui-build-status-hud {
  position: fixed;
  top: 16px;
  right: 18px;
  z-index: 2147483002;
  pointer-events: none;
  padding: 8px 11px;
  border: 1px solid rgba(143,232,184,.16);
  border-radius: 10px;
  background: rgba(2,8,6,.48);
  backdrop-filter: blur(10px);
  color: #9bc4b2;
  font: 9px/1.2 Inter, Segoe UI, system-ui, sans-serif;
  letter-spacing: .16em;
  text-transform: uppercase;
}
""",
        markup='<div id="jarvis-ui-build-status-hud">JARVIS · STATUS HUD</div>',
        protected=True,
    ),
    UIBuild(**NEURAL_MESH_BUILTIN),
)


class UIBuildStore:
    """File-backed UI build catalog with arbitrary build count and safe rollback."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else default_store_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "state.json"
        self._lock = threading.RLock()
        self._ensure_builtins()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _json_write_atomic(path: Path, payload: Mapping[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        finally:
            temp_path.unlink(missing_ok=True)

    @staticmethod
    def _text_write_atomic(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        finally:
            temp_path.unlink(missing_ok=True)

    @staticmethod
    def _validate_text(value: object, field: str, maximum: int) -> str:
        text = str(value or "")
        if len(text.encode("utf-8")) > maximum:
            raise ValueError(f"{field} exceeds {maximum} bytes")
        return text

    @classmethod
    def _normalize(cls, payload: Mapping[str, object], *, protected: bool = False) -> UIBuild:
        raw_id = str(payload.get("id", "")).strip().lower()
        if not _BUILD_ID.fullmatch(raw_id):
            raise ValueError("UI build id must match ^[a-z0-9][a-z0-9._-]{0,63}$")
        name = cls._validate_text(payload.get("name"), "name", _MAX_NAME_LENGTH).strip()
        if not name:
            raise ValueError("UI build name is required")
        version = cls._validate_text(payload.get("version", "1.0.0"), "version", _MAX_VERSION_LENGTH).strip() or "1.0.0"
        description = cls._validate_text(payload.get("description", ""), "description", _MAX_DESCRIPTION_LENGTH)
        css = cls._validate_text(payload.get("css", ""), "css", _MAX_ASSET_BYTES)
        markup = cls._validate_text(payload.get("markup", ""), "markup", _MAX_ASSET_BYTES)
        script = cls._validate_text(payload.get("script", ""), "script", _MAX_ASSET_BYTES)
        if _FORBIDDEN_MARKUP.search(markup):
            raise ValueError("UI build markup may not contain scripts, embedded frames/objects, inline event handlers, or javascript URLs")
        return UIBuild(
            id=raw_id,
            name=name,
            version=version,
            description=description,
            css=css,
            markup=markup,
            script=script,
            protected=protected,
        )

    @staticmethod
    def _safe_build_id(build_id: str) -> str:
        normalized = str(build_id).strip().lower()
        if not _BUILD_ID.fullmatch(normalized):
            raise ValueError("invalid UI build id")
        return normalized

    def _build_dir(self, build_id: str) -> Path:
        return self.root / self._safe_build_id(build_id)

    def _manifest_path(self, build_id: str) -> Path:
        return self._build_dir(build_id) / "manifest.json"

    def _read_build(self, build_id: str) -> UIBuild:
        build_dir = self._build_dir(build_id)
        manifest_path = self._manifest_path(build_id)
        if not manifest_path.is_file():
            raise KeyError(f"unknown UI build: {build_id}")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            build_created_at = str(manifest.get("created_at", "") or "")
            build_updated_at = str(manifest.get("updated_at", "") or "")
            build = self._normalize(manifest, protected=bool(manifest.get("protected", False)))
            css_path = build_dir / "style.css"
            markup_path = build_dir / "index.html"
            script_path = build_dir / "script.js"
            css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
            markup = markup_path.read_text(encoding="utf-8") if markup_path.exists() else ""
            script = script_path.read_text(encoding="utf-8") if script_path.exists() else ""
            validated_assets = self._normalize(
                {
                    **build.metadata(),
                    "css": css,
                    "markup": markup,
                    "script": script,
                },
                protected=build.protected,
            )
            return replace(
                validated_assets,
                created_at=build_created_at,
                updated_at=build_updated_at,
            )
        except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid UI build '{build_id}': {type(exc).__name__}") from exc

    def _state(self) -> dict[str, object]:
        default = {"active": DEFAULT_BUILD_ID, "history": []}
        if not self.state_path.exists():
            return default
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            active = str(raw.get("active", DEFAULT_BUILD_ID))
            history = [str(item) for item in raw.get("history", []) if isinstance(item, str)]
            return {"active": active, "history": history[-MAX_ROLLBACK_HISTORY:]}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return default

    def _write_state(self, active: str, history: list[str]) -> None:
        clean_history = [item for item in history if item and item != active][-MAX_ROLLBACK_HISTORY:]
        self._json_write_atomic(self.state_path, {"active": active, "history": clean_history})

    def _write_build(self, build: UIBuild) -> None:
        build_dir = self._build_dir(build.id)
        build_dir.mkdir(parents=True, exist_ok=True)
        self._json_write_atomic(build_dir / "manifest.json", build.metadata())
        self._text_write_atomic(build_dir / "style.css", build.css)
        self._text_write_atomic(build_dir / "index.html", build.markup)
        self._text_write_atomic(build_dir / "script.js", build.script)

    def _ensure_builtins(self) -> None:
        with self._lock:
            for builtin in _BUILTIN_BUILDS:
                try:
                    existing = self._read_build(builtin.id)
                except (KeyError, ValueError):
                    existing = None
                if existing is None or existing.protected != builtin.protected:
                    stamp = self._now()
                    self._write_build(UIBuild(**{**builtin.payload(), "created_at": stamp, "updated_at": stamp}))
            state = self._state()
            try:
                self._read_build(str(state.get("active", DEFAULT_BUILD_ID)))
            except (KeyError, ValueError):
                self._write_state(DEFAULT_BUILD_ID, [])

    def list(self) -> list[UIBuild]:
        with self._lock:
            items: list[UIBuild] = []
            for child in self.root.iterdir():
                if not child.is_dir() or child.name.startswith("."):
                    continue
                try:
                    items.append(self._read_build(child.name))
                except (KeyError, ValueError):
                    continue
            return sorted(items, key=lambda item: (item.id != DEFAULT_BUILD_ID, item.name.casefold()))

    def get(self, build_id: str) -> UIBuild:
        with self._lock:
            return self._read_build(self._safe_build_id(build_id))

    def active(self) -> UIBuild:
        with self._lock:
            state = self._state()
            active_id = str(state.get("active", DEFAULT_BUILD_ID))
            try:
                return self._read_build(active_id)
            except (KeyError, ValueError):
                self._write_state(DEFAULT_BUILD_ID, [])
                return self._read_build(DEFAULT_BUILD_ID)

    def save(self, payload: Mapping[str, object]) -> UIBuild:
        with self._lock:
            candidate = self._normalize(payload)
            existing: UIBuild | None = None
            try:
                existing = self._read_build(candidate.id)
            except (KeyError, ValueError):
                existing = None
            if existing is not None and existing.protected:
                raise ValueError(f"protected UI build cannot be replaced: {candidate.id}")
            stamp = self._now()
            created_at = existing.created_at if existing is not None and existing.created_at else stamp
            build = UIBuild(**{**candidate.payload(), "created_at": created_at, "updated_at": stamp})
            self._write_build(build)
            return build

    def delete(self, build_id: str) -> None:
        with self._lock:
            target = self.get(build_id)
            if target.protected:
                raise ValueError("protected UI builds cannot be deleted")
            state = self._state()
            if str(state.get("active")) == target.id:
                raise ValueError("active UI build cannot be deleted; switch builds or restore the default first")
            shutil.rmtree(self._build_dir(target.id))

    def activate(self, build_id: str) -> UIBuild:
        with self._lock:
            target = self.get(build_id)
            state = self._state()
            current = str(state.get("active", DEFAULT_BUILD_ID))
            history = [str(item) for item in state.get("history", [])]
            if target.id != current:
                history.append(current)
                self._write_state(target.id, history)
            return target

    def rollback(self) -> UIBuild:
        with self._lock:
            state = self._state()
            history = [str(item) for item in state.get("history", [])]
            while history:
                candidate = history.pop()
                try:
                    target = self.get(candidate)
                except (KeyError, ValueError):
                    continue
                self._write_state(target.id, history)
                return target
            self._write_state(DEFAULT_BUILD_ID, [])
            return self.get(DEFAULT_BUILD_ID)

    def _read_metadata(self, build_id: str) -> UIBuild:
        safe_id = self._safe_build_id(build_id)
        manifest_path = self._manifest_path(safe_id)
        if not manifest_path.is_file():
            raise KeyError(f"unknown UI build: {safe_id}")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            normalized = self._normalize(manifest, protected=bool(manifest.get("protected", False)))
            return UIBuild(
                **{
                    **normalized.payload(),
                    "created_at": str(manifest.get("created_at", "") or ""),
                    "updated_at": str(manifest.get("updated_at", "") or ""),
                }
            )
        except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid UI build '{safe_id}': {type(exc).__name__}") from exc

    def catalog(self) -> list[dict[str, object]]:
        with self._lock:
            active_id = self.active().id
            items: list[dict[str, object]] = []
            for child in self.root.iterdir():
                if not child.is_dir() or child.name.startswith("."):
                    continue
                try:
                    build = self._read_metadata(child.name)
                except (KeyError, ValueError):
                    continue
                items.append({**build.metadata(), "active": build.id == active_id})
            return sorted(items, key=lambda item: (item["id"] != DEFAULT_BUILD_ID, str(item["name"]).casefold()))


def build_manager_script() -> str:
    return r'''(() => {
  "use strict";
  if (window.__jarvisUiBuildManagerInstalled) return;
  window.__jarvisUiBuildManagerInstalled = true;

  const style = document.createElement("style");
  style.id = "jarvis-ui-build-manager-style";
  style.textContent = `
    #jarvis-ui-build-toggle {
      position:fixed; right:18px; bottom:18px; z-index:2147483647;
      border:1px solid rgba(143,232,184,.22); border-radius:10px;
      padding:8px 10px; color:#9fc9b6; background:rgba(2,8,6,.54);
      backdrop-filter:blur(10px); cursor:pointer; font:9px/1.2 Inter,Segoe UI,system-ui,sans-serif;
      letter-spacing:.14em; text-transform:uppercase; pointer-events:auto;
    }
    #jarvis-ui-build-panel {
      position:fixed; right:18px; bottom:58px; width:min(460px,calc(100vw - 36px));
      max-height:min(72vh,720px); z-index:2147483647; display:none; pointer-events:auto;
      border:1px solid rgba(143,232,184,.16); border-radius:14px;
      background:rgba(2,7,5,.86); backdrop-filter:blur(16px);
      box-shadow:0 18px 60px rgba(0,0,0,.35); color:#dff5e9;
      font:11px/1.35 Inter,Segoe UI,system-ui,sans-serif; overflow:hidden;
    }
    #jarvis-ui-build-panel.active { display:flex; flex-direction:column; }
    .juib-head { display:flex; justify-content:space-between; align-items:center; gap:10px; padding:13px 14px; border-bottom:1px solid rgba(143,232,184,.10); }
    .juib-title { font-size:10px; letter-spacing:.18em; }
    .juib-sub { color:#6f887f; font-size:9px; }
    .juib-actions { display:flex; gap:6px; }
    .juib-btn { border:1px solid rgba(143,232,184,.14); border-radius:8px; padding:6px 8px; color:#9fc9b6; background:rgba(255,255,255,.02); cursor:pointer; font:9px/1.2 Inter,Segoe UI,system-ui,sans-serif; }
    .juib-btn:hover { border-color:rgba(143,232,184,.35); color:#e7fff2; }
    #jarvis-ui-build-list { overflow:auto; padding:10px; display:flex; flex-direction:column; gap:7px; }
    .juib-row { display:grid; grid-template-columns:1fr auto; gap:9px; padding:10px; border:1px solid rgba(143,232,184,.09); border-radius:10px; background:rgba(255,255,255,.018); }
    .juib-row.active { border-color:rgba(89,230,155,.30); }
    .juib-row b { display:block; font-size:10px; font-weight:500; color:#d8f3e6; }
    .juib-row small { display:block; margin-top:3px; color:#718a81; font-size:9px; }
    .juib-row em { display:inline-block; margin-top:6px; color:#668077; font-size:8px; letter-spacing:.10em; font-style:normal; }
    #jarvis-ui-build-editor { display:none; padding:10px; border-top:1px solid rgba(143,232,184,.10); }
    #jarvis-ui-build-editor.active { display:block; }
    .juib-field { width:100%; box-sizing:border-box; margin:0 0 7px; padding:8px 9px; border:1px solid rgba(143,232,184,.13); border-radius:8px; color:#e7fff2; background:rgba(0,0,0,.22); outline:none; font:9px/1.4 Consolas,monospace; }
    textarea.juib-field { min-height:68px; resize:vertical; }
    #juib-editor-markup { min-height:74px; }
    #juib-editor-css, #juib-editor-js { min-height:88px; }
    .juib-note { color:#637a72; font-size:8px; margin:-2px 0 8px; }
  `;
  document.head.appendChild(style);

  const toggle = document.createElement("button");
  toggle.id = "jarvis-ui-build-toggle";
  toggle.textContent = "UI BUILDS";
  document.body.appendChild(toggle);

  const panel = document.createElement("div");
  panel.id = "jarvis-ui-build-panel";
  panel.innerHTML = `
    <div class="juib-head">
      <div><div class="juib-title">UI BUILD GALLERY</div><div class="juib-sub">Unlimited local builds · instant switch · rollback</div></div>
      <div class="juib-actions"><button class="juib-btn" id="juib-new">NEW</button><button class="juib-btn" id="juib-rollback">ROLLBACK</button><button class="juib-btn" id="juib-close">CLOSE</button></div>
    </div>
    <div id="jarvis-ui-build-list"></div>
    <div id="jarvis-ui-build-editor">
      <input class="juib-field" id="juib-editor-id" placeholder="build-id (lowercase, hyphens allowed)" />
      <input class="juib-field" id="juib-editor-name" placeholder="Build name" />
      <input class="juib-field" id="juib-editor-version" placeholder="Version (e.g. 1.0.0)" value="1.0.0" />
      <input class="juib-field" id="juib-editor-description" placeholder="Description" />
      <textarea class="juib-field" id="juib-editor-css" placeholder="CSS"></textarea>
      <textarea class="juib-field" id="juib-editor-markup" placeholder="HTML markup (no script tags or inline event handlers)"></textarea>
      <textarea class="juib-field" id="juib-editor-js" placeholder="Optional JavaScript"></textarea>
      <div class="juib-note">Saved builds are inactive until selected. The base Fullstack visualizer and command bar remain underneath every build.</div>
      <button class="juib-btn" id="juib-save">SAVE BUILD</button>
    </div>
  `;
  document.body.appendChild(panel);

  const list = document.getElementById("jarvis-ui-build-list");
  const editor = document.getElementById("jarvis-ui-build-editor");
  const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[ch]));

  function api() { return window.pywebview && window.pywebview.api; }

  async function applyPayload(payload) {
    const oldLayer = document.getElementById("jarvis-ui-build-layer");
    if (oldLayer) oldLayer.remove();
    const oldStyle = document.getElementById("jarvis-ui-build-style");
    if (oldStyle) oldStyle.remove();

    if (payload && payload.css) {
      const buildStyle = document.createElement("style");
      buildStyle.id = "jarvis-ui-build-style";
      buildStyle.textContent = String(payload.css);
      document.head.appendChild(buildStyle);
    }
    const layer = document.createElement("div");
    layer.id = "jarvis-ui-build-layer";
    layer.dataset.buildId = String(payload && payload.id || "");
    layer.innerHTML = String(payload && payload.markup || "");
    if (!layer.children.length && !payload.script) {
      layer.remove();
      return;
    }
    document.body.appendChild(layer);

    if (payload && payload.script) {
      try {
        const runner = new Function("root", String(payload.script));
        runner(layer);
      } catch (error) {
        layer.remove();
        const failedStyle = document.getElementById("jarvis-ui-build-style");
        if (failedStyle) failedStyle.remove();
        window.setTimeout(() => window.alert("Jarvis UI build failed safely: " + String(error && error.message || error).slice(0, 240)), 0);
        throw error;
      }
    }
  }

  function closeEditor() { editor.classList.remove("active"); }

  async function refresh() {
    if (!api() || !api().ui_builds_catalog) return;
    try {
      const catalog = await api().ui_builds_catalog();
      list.innerHTML = (Array.isArray(catalog) ? catalog : []).map(item => (
        '<div class="juib-row' + (item.active ? ' active' : '') + '">' +
        '<div><b>' + esc(item.name) + (item.active ? ' · ACTIVE' : '') + '</b>' +
        '<small>' + esc(item.description) + '</small>' +
        '<em>' + esc(item.id) + ' · v' + esc(item.version) + (item.protected ? ' · BUILT-IN' : '') + '</em></div>' +
        '<div><button class="juib-btn juib-activate" data-id="' + esc(item.id) + '">' + (item.active ? 'ACTIVE' : 'USE') + '</button></div></div>'
      )).join("") || '<div class="juib-row"><small>No valid UI builds.</small></div>';
      list.querySelectorAll(".juib-activate").forEach(button => {
        button.addEventListener("click", async () => {
          const id = button.dataset.id;
          let activatedPayload = null;
          try {
            activatedPayload = await api().ui_builds_activate(id);
            await applyPayload(activatedPayload);
            await refresh();
          } catch (error) {
            if (activatedPayload && api().ui_builds_rollback) {
              try {
                const fallback = await api().ui_builds_rollback();
                await applyPayload(fallback);
                await refresh();
              } catch (_) {}
            }
            window.alert("Could not activate UI build: " + String(error && error.message || error));
          }
        });
      });
    } catch (error) {
      list.innerHTML = '<div class="juib-row"><small>UI build catalog unavailable. Base Jarvis UI remains online.</small></div>';
    }
  }

  toggle.addEventListener("click", () => {
    panel.classList.toggle("active");
    if (panel.classList.contains("active")) refresh();
  });
  window.addEventListener("keydown", event => {
    if (event.ctrlKey && event.shiftKey && String(event.key).toLowerCase() === "b") {
      event.preventDefault();
      panel.classList.toggle("active");
      if (panel.classList.contains("active")) refresh();
    }
  });
  document.getElementById("juib-close").addEventListener("click", () => panel.classList.remove("active"));
  document.getElementById("juib-new").addEventListener("click", () => {
    editor.classList.toggle("active");
    if (editor.classList.contains("active")) document.getElementById("juib-editor-id").focus();
  });
  document.getElementById("juib-rollback").addEventListener("click", async () => {
    try {
      const payload = await api().ui_builds_rollback();
      await applyPayload(payload);
      await refresh();
    } catch (error) {
      window.alert("Could not roll back UI build: " + String(error && error.message || error));
    }
  });
  document.getElementById("juib-save").addEventListener("click", async () => {
    try {
      const payload = await api().ui_builds_save({
        id: document.getElementById("juib-editor-id").value,
        name: document.getElementById("juib-editor-name").value,
        version: document.getElementById("juib-editor-version").value,
        description: document.getElementById("juib-editor-description").value,
        css: document.getElementById("juib-editor-css").value,
        markup: document.getElementById("juib-editor-markup").value,
        script: document.getElementById("juib-editor-js").value
      });
      editor.classList.remove("active");
      await refresh();
      window.alert("UI build saved: " + String(payload.name || payload.id));
    } catch (error) {
      window.alert("Could not save UI build: " + String(error && error.message || error));
    }
  });

  async function hydrate() {
    if (!api() || !api().ui_builds_active) return;
    let activePayload = null;
    try {
      activePayload = await api().ui_builds_active();
      await applyPayload(activePayload);
      refresh();
    } catch (_) {
      if (activePayload && api().ui_builds_rollback) {
        try {
          const fallback = await api().ui_builds_rollback();
          await applyPayload(fallback);
          refresh();
        } catch (_) {
          // Default/base Jarvis UI remains authoritative even if the optional manager fails.
        }
      }
    }
  }

  window.addEventListener("pywebviewready", hydrate, { once: true });
  if (window.pywebview && window.pywebview.api) hydrate();
})();
'''


def install(desktop_module: Any) -> None:
    """Install the UI build manager as an additive layer over the existing desktop host."""
    base_api = desktop_module.JarvisWebApi
    store = UIBuildStore()

    class UIBuildWebApi(base_api):
        def __init__(self, host: Any) -> None:
            super().__init__(host)

        def ui_builds_catalog(self) -> list[dict[str, object]]:
            return store.catalog()

        def ui_builds_active(self) -> dict[str, object]:
            return store.active().payload()

        def ui_builds_activate(self, build_id: str) -> dict[str, object]:
            return store.activate(build_id).payload()

        def ui_builds_rollback(self) -> dict[str, object]:
            return store.rollback().payload()

        def ui_builds_save(self, payload: Mapping[str, object]) -> dict[str, object]:
            if not isinstance(payload, Mapping):
                raise TypeError("UI build payload must be an object")
            return store.save(payload).payload()

        def ui_builds_delete(self, build_id: str) -> dict[str, object]:
            store.delete(build_id)
            return {"ok": True, "id": str(build_id)}

    desktop_module.JarvisWebApi = UIBuildWebApi
    desktop_module.TEXT_INPUT_SCRIPT += "\n" + build_manager_script()
