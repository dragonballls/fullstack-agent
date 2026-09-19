# fullstack-agent

> **Jarvis profile:** a cloud-first AI assistant integration layer with memory, voice, face, hands, guarded computer/browser control, self-coding, accounts, and Windows maintenance.

This fork preserves the upstream `fullstack-agent` setup flow, but the **Jarvis profile is the primary product contract for this fork**. Jarvis uses OmniRoute as its conversational/agent brain; Claude Code is not required by the Jarvis profile.

**Windows product boundary:** this repository is both the Jarvis integration/source layer and the source of the verified standalone Windows `Jarvis.exe` release. The normal end-user product is the single-file executable; Python, a virtual environment, a source checkout, and a separate Fullstack Agent checkout are developer/build concerns only. Target-machine credentials, permissions, microphones, webcams, browsers, and external service authorization still have to be configured where required. See `JARVIS_DOWNLOAD.md` and `JARVIS_SETUP.md`.

## What the upstream fullstack-agent stack provides

Four pieces, each its own open repo, can still be assembled by the upstream setup flow:

- **The mind: [ai-memory-vault](https://github.com/jaredrhod/ai-memory-vault).** A persistent memory built on plain text files your AI reads and writes.
- **The mouth: [backtalk](https://github.com/jaredrhod/backtalk).** Voice input/output for the upstream fullstack-agent stack.
- **The face: [ai-visualizer](https://github.com/jaredrhod/ai-visualizer).** Visualizers for the upstream stack.
- **The hands: [barehands](https://github.com/jaredrhod/barehands).** Optional webcam hand interaction for the upstream stack.

The Jarvis Windows release embeds pinned revisions of the upstream components needed by its native Fullstack presentation and voice contract. Their upstream repositories remain separate projects, while the release workflow vendors the required source into the executable.

## Jarvis integration

This fork ships independent Jarvis extensions without replacing the upstream stack:

- **`self_coding/`** is a guarded cloud coding engine. It requires a clean Git tree, uses an isolated branch, verifies changes before committing, and rolls failed passes back to the exact starting point.
- **`quality_of_life/`** provides guarded computer control, browser automation, location/God's Eye context, account access, multi-AI cloud routing, and Windows maintenance.
- **Webcam hand control** provides guarded system-wide pointer movement, click/drag/scroll gestures, tracking-loss handling, emergency pause, and an explicit activation boundary.
- **Background-efficient mode** keeps local voice wake listening available while allowing foreground-only presentation work to suspend when minimized; active hand control remains independently managed. See `docs/jarvis-background-mode.md`.
- **Phone/device integration** provides Android companion and device-adapter contracts behind explicit permissions and readiness checks.

The Jarvis profile uses **OmniRoute only** as its conversational/agent brain. Claude Code and a Claude subscription are not required by the Jarvis profile and are not valid Jarvis fallbacks.

The Jarvis voice profile adds local wake-word activation: after microphone permission is granted, wake detection can run locally and Jarvis does not send cloud requests until the wake word is accepted. See `JARVIS_SETUP.md` and `JARVIS_VOICE.md`.

The preferred Jarvis speech output is **ElevenLabs**. Backtalk supplies microphone/speech input and push-to-talk behavior, while ElevenLabs supplies the spoken response. They are I/O components only, not Jarvis brains. **Kokoro** remains present in the development/build dependency set for upstream compatibility; it is not the Jarvis desktop speech-output engine.

Jarvis also includes a scoped multi-account model for Google, Microsoft, GitHub, YouTube, Instagram, and generic web services. OAuth/user consent, provider scopes, local capability policy, and confirmation gates remain required; account credentials are kept behind a runtime credential broker.

## Jarvis Windows launch

For end users on Windows, the normal launch path is the verified **single-file `Jarvis.exe`** from the GitHub `latest` release. Double-clicking that executable is the supported product launch path; it opens the native Fullstack visualizer and does not require a persistent PowerShell console.

For repository developers, `scripts/start-jarvis.ps1` is a helper for launching a locally built `dist\\Jarvis.exe`. It does not define the end-user installation contract and should not be confused with the separate upstream `start.bat` flow.

## Jarvis installation and download

For the Jarvis profile, start with `JARVIS_DOWNLOAD.md` and `JARVIS_SETUP.md`.

The release workflow validates the source and runtime contracts on Ubuntu and Windows with Python 3.11, 3.12, and 3.13; checks dependency consistency; compiles the Python modules; runs the complete regression suite; runs Windows-maintenance tests; fetches pinned Fullstack Agent components; builds the native single-file executable; and smoke-tests the frozen visualizer and packaged Jarvis host.

A semantic-version tag (`vMAJOR.MINOR.PATCH`) publishes the verified `Jarvis.exe` directly as a GitHub Release asset. The rolling `latest` release is also refreshed from the same passing Windows gate on `main`.

### Upstream fullstack-agent installation

The commands below are retained only for the **upstream fullstack-agent setup flow**. They are not the Jarvis installation contract.

Mac and Linux:

```text
mkdir -p ~/my-agent && cd ~/my-agent && git clone https://github.com/jaredrhod/fullstack-agent && cd fullstack-agent && claude "set me up"
```

Windows (PowerShell):

```text
$d="$env:USERPROFILE\\.local\\bin"; if (Test-Path "$d\\claude.exe") { $env:Path="$d;$env:Path" }; New-Item -ItemType Directory -Force -Path $HOME\\my-agent | Out-Null; cd $HOME\\my-agent; if (-not (Test-Path fullstack-agent\\fullstack-agent.md)) { Invoke-WebRequest https://github.com/jaredrhod/fullstack-agent/archive/refs/heads/main.zip -OutFile fsa.zip; Expand-Archive fsa.zip . -Force; New-Item -ItemType Directory -Force -Path fullstack-agent | Out-Null; Get-ChildItem fullstack-agent-main -Force | Copy-Item -Destination fullstack-agent -Recurse -Force; Remove-Item fullstack-agent-main -Recurse -Force; Remove-Item fsa.zip }; cd fullstack-agent; if (Get-Command claude -ErrorAction SilentlyContinue) { claude "set me up" } else { Write-Output "Claude Code is not installed yet. Install it first at https://jaredrhod.com/start then paste this again." }
```

## Upstream already-built pieces

The upstream wizard can adopt an existing memory vault, voice line, or visualizer. Those behaviors remain documented here for compatibility with the original project. The Jarvis profile, however, uses the contracts in `JARVIS_SETUP.md`, `JARVIS_VOICE.md`, and `JARVIS_DOWNLOAD.md` rather than the upstream Claude-only setup path.

## After upstream setup

The original upstream shortcuts and `start.sh` / `start.bat` continue to describe that upstream multi-repository stack. They are **not** the Jarvis Windows product launcher. For Jarvis, use the verified `Jarvis.exe` release asset for normal operation.

## Safety and runtime boundaries

- Jarvis must not bypass capability policy, confirmation hooks, emergency stop, cancellation, self-coding safeguards, or browser/domain restrictions.
- Microphone wake detection stays local until wake acceptance.
- Webcam hand control is explicitly activated, fails closed on tracking loss, and remains independently stoppable.
- Background mode reduces foreground presentation work; it does not claim zero CPU/RAM while active microphone or hand tracking is running.
- Unsupported external operations are reported as unsupported instead of being fabricated.
- Credentials and refresh tokens are kept behind the runtime credential broker and never stored in tracked configuration or returned to the model.

## Troubleshooting and readiness

Use `JARVIS_READINESS.md` and `readiness.py` for machine-specific checks. A `READY` result means the required local prerequisites detected by that diagnostic are present. Optional integrations may still report warnings.

The authoritative Windows/product distribution contract is `JARVIS_DOWNLOAD.md`, with `JARVIS_SETUP.md` defining the normal end-user setup and `JARVIS_VOICE.md` defining the voice contract. Historical plan documents and stale feature branches do not supersede the current `main` implementation.

## The rest of it

The upstream project remains free and open under AGPL-3.0-or-later. See `LICENSE` for full terms.

## License

Copyright (c) 2026 Jared Rhodenizer.

Licensed under the GNU Affero General Public License, version 3 or later (AGPL-3.0-or-later).