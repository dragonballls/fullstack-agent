# Jarvis setup

This is the authoritative setup contract for the Jarvis Windows desktop product.

## Windows product

The supported end-user product is a single verified/release-published `Jarvis.exe`. Normal use does not require Python, a virtual environment, a source checkout, a separate Fullstack Agent checkout, or a persistent PowerShell window.

Download the `Jarvis.exe` asset from the verified GitHub `latest` release. Double-clicking that executable is the normal Windows launch path.

The executable contains the Jarvis runtime, a pinned self-contained OmniRoute gateway (Node.js 24.21.0 + OmniRoute 3.8.50), the optional embedded Prism/free-astra compatibility bridge, and the pinned Fullstack Agent presentation components used by the native visualizer and Backtalk voice bridge. The Prism bridge contains no local LLM: its inference remains remote. Jarvis keeps one guarded planner/tool execution path; the embedded Fullstack components are presentation and I/O adapters.

## What first launch may create

Jarvis may create these machine-local files under `%LOCALAPPDATA%\\Jarvis`:

- `logs\\desktop.log` for startup/runtime diagnostics
- `logs\\voice-bridge.log` for voice adapter errors without ambient-audio transcripts
- `backtalk.json` for local voice configuration
- `signals\\` for the local visualizer signal bus
- `updates\\` for verified staged self-updates

These files are runtime state and are not source dependencies for the application.

## Runtime and cloud configuration

The **OmniRoute only** default routing layer is the normal Jarvis path. Claude Code and a Claude subscription are not required for Jarvis. Direct Claude routing is not a Jarvis fallback, and the supported disabled-override state is `JARVIS_ALLOW_CLAUDE=false`.

When a Prism session is explicitly configured, Jarvis also enables the optional remote Prism/Astra provider target. That target runs only as a local compatibility process; it does not run an LLM on the PC. Prism/Astra remains an unsupported external integration whose model availability can change, so OmniRoute remains the automatic fallback.

Speech engines such as Kokoro, Faster Whisper, or an externally configured speech provider are I/O components only. They never become a replacement planner/tool executor.

Live cloud requests still require at least one configured provider credential. On first launch, Jarvis starts the embedded OmniRoute gateway automatically; open AI Provider Settings from the command surface, select a provider, paste its API key, and use CONNECT & TEST. Jarvis passes the secret directly to OmniRoute and clears its own input; credentials are stored by OmniRoute in its local credential store and never enter tracked configuration. The gateway's local routing endpoint is fixed to `http://127.0.0.1:20128/v1`.

### Optional Prism/Astra bridge

The embedded Prism bridge is disabled in practice until a Prism session file exists. The default Windows location is `%LOCALAPPDATA%\\Jarvis\\Prism\\session.json`; `JARVIS_PRISM_SESSION` can point to a different file and `JARVIS_PRISM_ENABLED=0` disables the bridge. Jarvis never scrapes browser cookies or silently collects credentials. When a valid session is present, the bridge listens only on `http://127.0.0.1:8319/v1` and exposes an OpenAI-compatible surface. The bridge's own Prism/Astra model availability is checked by the upstream service at request time; an unsupported Astra request can fall back to a Prism model that is still accepted.

## Voice

The native desktop build embeds the pinned Backtalk source and the Jarvis voice bridge. Default Backtalk settings are configured in `%LOCALAPPDATA%\\Jarvis\\backtalk.json` and can be changed through supported Jarvis configuration/environment settings.

Microphone and speaker access are machine-specific. A missing device, denied permission, or unavailable audio dependency must not prevent the Fullstack visualizer from opening; Jarvis records the degraded voice state and keeps the main desktop interface available.

See `JARVIS_VOICE.md` for the current voice/I/O contract and the real speech test procedure.

## Fullstack interface

At startup Jarvis brings up the embedded Fullstack visualizer on loopback port `8790` and opens it in the native pywebview window. The old 640-by-118 Tk chat bar is not the Jarvis product UI.

The visualizer is started before heavier Jarvis initialization so the presentation surface can become available even when core/cloud initialization takes longer on first launch.

## Self-update

The executable checks the verified rolling GitHub `latest` release periodically. An update is considered available only when the release commit differs from the embedded build commit. Jarvis downloads only the `Jarvis.exe` release asset from GitHub, verifies the release-provided SHA-256 digest, then uses a hidden handoff process to replace the running executable and restart it.

An update failure leaves the currently running Jarvis instance in place. Normal operation does not restart for every repository commit; only a newly published release with a different embedded commit is eligible for the update path.

## Optional capabilities

Hand control, browser/device integrations, account connections, location features, and Windows maintenance remain behind their existing capability and confirmation policies. Optional capability failure must degrade the specific feature rather than take down the desktop visualizer.

Hosted CI can verify source contracts, imports, routing, OmniRoute provisioning, embedded-runtime versioning, packaging, and the frozen visualizer/Backtalk startup path. It cannot certify a particular PC's microphone, speakers, camera, provider credentials, OAuth grants, or hardware-specific behavior.

## Developer-only build path

Repository development uses Python and the project build scripts. That build environment is not required by end users. The authoritative release artifact is the one-file `dist\\Jarvis.exe` produced by the `Jarvis full release gate` workflow after regression, packaging, and frozen startup checks pass.
