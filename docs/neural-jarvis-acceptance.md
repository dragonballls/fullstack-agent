# Neural JARVIS Build #2 — Acceptance Matrix

## Core world
- Fully 3D WebGL2 neural world with blue holographic Jarvis styling.
- Instanced liquid-cell neurons with idle deformation and energy-driven glow.
- Similar-neuron attraction plus collision/spacing relaxation and bounded fluid offsets.
- Grab/detach/reconnect behavior with fragment particles.
- Mitosis-style creation animation and retirement/apoptosis lifecycle visualization.
- Persistent entities and relationships with bounded snapshots and event sequencing.

## Real-world neural entities
- Applications, windows, browsers/tabs/pages, files/folders/drives, repositories/branches/commits/PRs/builds/artifacts/tests, agents, workflows, tasks, memory, devices, accounts, services, locations, processes, performance, notifications, search results, and temporary objects.
- Deterministic placement plus visible/off-screen culling.
- Observable task neurons track real orchestration stages and failure/waiting/completion states.

## Neural Lens
- Text search.
- Type, lifecycle, status, source, connected-to, and recency filters.
- Find/focus and Follow the active task.
- Neural Trace playback through observed graph relationships.
- Far-zoom minimap.

## Conversation and observation
- Persistent typed Talk-to-Jarvis input.
- Existing voice bridge remains enabled by the Fullstack host.
- Observation mode is off by default.
- Explicit “show me what you are doing” mode exposes high-level execution breadcrumbs only; private chain-of-thought is never surfaced.

## Shapes
- Procedural droplet, sphere, crystal, cube, torus, capsule, ring, star, orbital, core, heart, gear, spiral, pyramid, wave, DNA-like, molecule, and arrow forms.
- Extensible parametric/freeform shape descriptors.
- Persistent custom shape library with save/resolve/delete support.
- Entity shape changes are applied without changing entity identity.

## God’s Eye
- Interactive 3D Earth sphere.
- 3D locator droplets.
- Guarded current location and saved locations.
- Provider-neutral device/phone/family feeds when an authorized live provider supplies coordinates.
- Place search from the existing God’s Eye geocoder.
- Locator selection and globe navigation.

## Spatial applications
- Generic app launch path: resolve/launch, detect new native window, spatialize when compatible, otherwise return a clean fallback.
- Native Win32 embedding foundation with reversible style/parent restoration.
- Spatial window discovery, focus, move/resize, show/hide, minimize/maximize/restore/close.
- Persistent spatial position/rotation/scale/pinning/workspace/mode/shape state.
- 2D and 3D surface presentation.
- Per-window resize and giant-window mode.
- Native embedded window drag/resize synchronization.
- Off-screen embedded surfaces are hidden to reduce composition work.
- Shutdown restores embedded windows.

## Performance
- Adaptive CPU/RAM/GPU/GPU-memory pressure sampling.
- Hysteresis-based maximum/balanced/performance/minimal budgets.
- Bounded neuron/relation/particle counts.
- Adaptive device-pixel-ratio and capture intervals.
- Cached NVIDIA telemetry discovery and cached Windows Graphics Capture capability probing.
- Hidden/background visual work is suppressed.

## Interaction
- Mouse orbit/zoom/select/grab.
- Hand-control loopback state integration.
- Pinch neuron/window grab.
- Multi-finger zoom support.
- Clickable Earth locators.
- Freeze/unfreeze world updates.

## Safety and reliability
- Existing capability policy/confirmation paths remain authoritative for mutating actions.
- Persistent storage uses atomic writes and schema validation.
- Activity telemetry never evicts active records; saturated telemetry no longer interrupts workflows.
- Workflow error summaries redact common secret formats.
- Native host HWND handling is pointer-sized.
- PR/release workflow concurrency is isolated by pull-request number.
- Release attestation verification is signer-workflow constrained.
- Build #1 remains protected and unchanged by Build #2.

## Verification
- Python regression suites cover neural world, events, persistence, shapes, performance, observation, location/globe, spatial launch/layout/embedding, hand state, workflows, workspaces, UI builds, voice, and universal capability contracts.
- JavaScript Neural JARVIS payload is syntax-checked in CI.
- Full GitHub Actions matrix covers self-coding safety, Windows maintenance, integration, quality-of-life, and the packaged Windows Jarvis release gate.
- Native release gate builds the single-file windowed Jarvis.exe, validates embedded upstream imports, launches the packaged visualizer, runs native GUI smoke tests, generates a signed attestation, and uploads the executable artifact.
