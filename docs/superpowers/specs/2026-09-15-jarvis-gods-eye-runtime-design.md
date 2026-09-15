# Jarvis God’s Eye Runtime Design

## Goal

Turn the existing optional quality-of-life layer into a real, capability-guarded runtime that can expose computer interaction, screen context, browser control, application/window/clipboard helpers, background jobs, cloud routing, and God’s Eye location/map context without replacing the existing self-coding, memory, voice, face, or hands systems.

## Design

The implementation stays isolated under `quality_of_life/` plus a thin runtime adapter. Existing modules remain valid public components. A registry resolves named tools to factories, a capability-aware orchestrator enforces deny-by-default permissions and confirmation hooks, and `runtime.py` provides a single dispatch surface for the agent.

God’s Eye is a separate adapter under `quality_of_life/gods_eye.py`. It provides place search/geocoding via pluggable HTTPS providers, current-location context via an explicitly supplied/resolvable provider, route/navigation URL generation, and an in-app map model. The service does not silently access precise location or external credentials: location access is a declared capability and may return `unavailable` when permission/provider data is absent. Place names such as “home”, “school”, “the airport”, or a city name resolve to structured places; the same structured object powers map rendering, context injection, and navigation actions.

## User-visible behavior

- Saying “open Tokyo” or “show me Tokyo” produces a God’s Eye place result and an in-app map state rather than merely launching a normal browser tab.
- Saying “where am I?” asks the location provider for the current coarse/precise level permitted by the caller and returns a structured location plus confidence/source metadata.
- Saying “take me to [place]” generates a route target and navigation context. Actual navigation is performed only by a caller-approved browser/app action.
- Saying “move here” or similar computer-control commands route through the existing mouse/keyboard capability and require confirmation.
- Screen captures, browser automation, clipboard, window/app controls, and background jobs are all explicit registered tools.
- When optional dependencies or providers are absent, the agent receives a typed unavailable result instead of a startup crash.

## Components

### `quality_of_life/manifest.py`

Registry entries become typed, lazily resolvable factories. The default registry includes `computer`, `screen`, `browser`, `windows`, `clipboard`, `background`, `cloud_router`, and `gods_eye`.

### `quality_of_life/windows.py`

Windows-only helper for enumerating, focusing, minimizing/maximizing, and closing windows through a narrow adapter. Window mutation requires `WINDOW_CONTROL`; app launch continues to use `APP_LAUNCH`.

### `quality_of_life/clipboard.py`

Clipboard read/write adapter with a bounded text-size limit. All access requires `CLIPBOARD`.

### `quality_of_life/runtime.py`

Constructs the default policy, lazily loads enabled tools, registers concrete actions with `QoLOrchestrator`, and exposes a typed `dispatch()` method. It never executes shell text supplied by a model. High-impact operations continue to flow through the confirmation hook.

### `quality_of_life/gods_eye.py`

Pure core types plus injectable providers:
- `GeoPoint`, `Place`, `Route`, and `LocationSnapshot` immutable data models.
- `Geocoder` protocol for place search.
- `LocationProvider` protocol for current-location permission/provider state.
- `MapRenderer` protocol for the in-app map payload.
- `GodsEye` service for `search`, `locate_me`, `route`, `open_place`, and `context`.
- HTTPS implementation uses standard-library networking only so the core remains lightweight and testable.

God’s Eye returns structured JSON-like dictionaries suitable for the existing agent/runtime layer. It never claims a location is known when no provider result exists.

## Safety and failure behavior

- Deny-by-default remains the invariant.
- Screen reads, location reads, clipboard reads, and repository reads are capability-gated.
- Mouse/keyboard/window/app/browser/repository-write/background mutations require the caller’s confirmation hook.
- No API keys, browser profiles, GPS identifiers, or private files are logged by the subsystem.
- URLs must be HTTPS/HTTP and navigation targets are generated from validated coordinates/place IDs.
- Network provider failures become typed provider errors and do not take down Jarvis startup.
- Optional dependencies remain optional; importing `quality_of_life` must remain safe on non-Windows systems and systems without Playwright/PyAutoGUI/MSS/Pillow.

## Integration boundaries

The default runtime adapter is additive. Existing self-coding remains the only component allowed to create and verify code changes. Existing voice/face/hands startup stays untouched except for documentation exposing the new optional runtime hook.

## Testing

Tests are layered:

1. Pure God’s Eye model/provider contract tests with fake geocoder/location providers.
2. QoL tool tests using fake OS/browser modules, including every capability gate and confirmation path.
3. Runtime registration/dispatch tests verifying every advertised action has a concrete handler.
4. Cross-platform import tests verifying optional Windows dependencies do not break Linux CI.
5. End-to-end contract tests exercising natural-language-like intents through a deterministic intent adapter and confirming the correct structured action is produced.
6. GitHub Actions matrix continues to run Python 3.11/3.12/3.13 on Windows and Ubuntu.

## Non-goals

This design does not add a new local LLM, does not expose unrestricted shell execution, does not silently collect precise location, and does not replace the existing visualizer/voice/face/hands architecture.
