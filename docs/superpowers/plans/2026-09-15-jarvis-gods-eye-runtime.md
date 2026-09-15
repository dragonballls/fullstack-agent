# Jarvis God’s Eye Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing quality-of-life subsystem a real, tested Jarvis runtime and add an in-app God’s Eye location/map workflow without breaking existing systems.

**Architecture:** Keep all new capability implementations under `quality_of_life/`, use lazy optional imports, and expose one capability-aware dispatcher. God’s Eye uses injectable geocoding and location providers plus a deterministic map payload so the core works without a vendor SDK or local LLM.

**Tech Stack:** Python 3.11–3.13, standard-library networking/JSON, existing PyAutoGUI/MSS/Pillow/Playwright optional adapters, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-15-jarvis-gods-eye-runtime-design.md`

## Global Constraints

- Deny-by-default capability policy remains mandatory.
- Mutating computer/browser/window/app/repository/background actions require confirmation.
- No unrestricted shell execution is added.
- No local LLM or Ollama dependency is introduced.
- Optional dependencies must not break imports on unsupported systems.
- Location is never claimed as known without a provider result.
- Credentials, browser profiles, private files, and precise location identifiers are never logged.
- Existing self-coding, voice, face, hands, and startup components remain additive and intact.

---

### Task 1: God’s Eye core contracts

**Files:**
- Create: `quality_of_life/gods_eye.py`
- Test: `tests/test_gods_eye.py`

**Interfaces:**
- `GeoPoint(latitude: float, longitude: float)` validates latitude/longitude bounds.
- `Place(name: str, point: GeoPoint, place_id: str | None, provider: str)` is immutable.
- `LocationSnapshot(point: GeoPoint | None, accuracy_m: float | None, permitted: bool, source: str)` is immutable.
- `Geocoder.search(query: str) -> list[Place]` protocol.
- `LocationProvider.current() -> LocationSnapshot` protocol.
- `GodsEye.search(query: str) -> list[Place]`.
- `GodsEye.locate_me() -> LocationSnapshot`.
- `GodsEye.route(origin: GeoPoint, destination: Place) -> dict[str, object]`.
- `GodsEye.context(query: str | None = None) -> dict[str, object]`.

- [ ] **Step 1: Write failing model/provider tests** covering coordinate validation, immutable values, empty queries, denied location, and route payload shape.
- [ ] **Step 2: Run `pytest tests/test_gods_eye.py -q` and verify the new tests fail.**
- [ ] **Step 3: Implement models/protocols/service with no network dependency.**
- [ ] **Step 4: Run the focused test suite and require PASS.**
- [ ] **Step 5: Commit `feat: add God’s Eye core contracts`.**

### Task 2: Provider adapters

**Files:**
- Modify: `quality_of_life/gods_eye.py`
- Create: `quality_of_life/location.py`
- Test: `tests/test_gods_eye_providers.py`

**Interfaces:**
- `NominatimGeocoder(endpoint: str = "https://nominatim.openstreetmap.org/search")` implements `Geocoder` through a bounded HTTPS JSON request.
- `SystemLocationProvider` returns `LocationSnapshot` from an injected callable or a platform adapter; default behavior is `permitted=False` when no provider is configured.
- Provider responses are normalized and malformed results are skipped rather than crashing the agent.

- [ ] **Step 1: Add fake-response tests for successful geocoding, malformed records, network failure, and denied location.**
- [ ] **Step 2: Run focused tests and confirm failure before implementation.**
- [ ] **Step 3: Implement bounded standard-library HTTPS adapter and location abstraction.**
- [ ] **Step 4: Verify no credential/location identifiers are logged and rerun tests.**
- [ ] **Step 5: Commit `feat: add guarded God’s Eye provider adapters`.**

### Task 3: Complete Windows QoL tools

**Files:**
- Create: `quality_of_life/clipboard.py`
- Create: `quality_of_life/windows.py`
- Modify: `quality_of_life/computer.py`
- Test: `tests/test_qol_tools.py`

**Interfaces:**
- `ClipboardController.read() -> str` and `write(text: str) -> None` under `Capability.CLIPBOARD`.
- `WindowsController.list_windows() -> list[dict[str, object]]`, `focus_window(identifier)`, `minimize_window(identifier)`, `maximize_window(identifier)`, `close_window(identifier)`.
- Existing `ComputerController` keeps `move`, `click`, `scroll`, `type_text`, `hotkey`, and `open_app` APIs unchanged.

- [ ] **Step 1: Write fake-module tests for clipboard and window operations plus all policy/confirmation branches.**
- [ ] **Step 2: Run focused tests and verify expected failures.**
- [ ] **Step 3: Implement lazy optional adapters; use explicit identifiers/handles and bounded text.**
- [ ] **Step 4: Run focused tests on Linux-compatible fakes.**
- [ ] **Step 5: Commit `feat: complete guarded Windows QoL controls`.**

### Task 4: Typed registry and runtime dispatcher

**Files:**
- Modify: `quality_of_life/manifest.py`
- Create: `quality_of_life/runtime.py`
- Modify: `quality_of_life/__init__.py`
- Test: `tests/test_qol_runtime.py`

**Interfaces:**
- `ToolSpec.factory` becomes a typed dotted-path string plus a resolver method; existing callers of `names()` and `get()` remain compatible.
- `JarvisRuntime(policy: CapabilityPolicy, confirmation: ConfirmationHook | None = None)` exposes `dispatch(capability, operation, **kwargs)` and `available_tools()`.
- Default actions cover computer, screen, browser, clipboard, windows, background, cloud router, and God’s Eye.

- [ ] **Step 1: Write registration and dispatch tests, including unknown action, denied capability, missing confirmation, and successful fake execution.**
- [ ] **Step 2: Run focused tests and verify failure.**
- [ ] **Step 3: Implement lazy factory resolution and action registration.**
- [ ] **Step 4: Run focused runtime tests and verify every advertised tool has handlers.**
- [ ] **Step 5: Commit `feat: add unified Jarvis capability runtime`.**

### Task 5: Intent bridge for natural location/computer commands

**Files:**
- Create: `quality_of_life/intents.py`
- Test: `tests/test_qol_intents.py`

**Interfaces:**
- `parse_intent(text: str) -> Intent` where `Intent.kind` is one of `place_search`, `locate_me`, `route`, `screen_read`, `computer_action`, or `chat`.
- `Intent` stores normalized query/action arguments but never executes actions.
- Location phrases map to God’s Eye operations; computer movement phrases map to explicit computer operations.

- [ ] **Step 1: Write deterministic parsing tests for “open/show Tokyo”, “where am I”, “take me to the airport”, “move mouse to 100 200”, and unknown chat.**
- [ ] **Step 2: Run tests and verify failure.**
- [ ] **Step 3: Implement conservative parsing with explicit patterns and no arbitrary code execution.**
- [ ] **Step 4: Run focused tests and verify all parsed operations route to typed intents.**
- [ ] **Step 5: Commit `feat: add safe QoL intent bridge`.**

### Task 6: God’s Eye in-app map state contract

**Files:**
- Modify: `quality_of_life/gods_eye.py`
- Create: `quality_of_life/gods_eye_map.py`
- Test: `tests/test_gods_eye_map.py`

**Interfaces:**
- `MapView(center: GeoPoint, zoom: int, markers: tuple[Place, ...], route: dict[str, object] | None)` immutable.
- `GodsEyeMap.build_search_view(places, selected=None) -> MapView`.
- `GodsEyeMap.build_location_view(snapshot) -> MapView | None`.
- `GodsEyeMap.build_route_view(origin, destination) -> MapView`.
- Serialization produces a UI-safe JSON object with no hidden network calls.

- [ ] **Step 1: Write view/serialization tests for one place, multiple results, current location, and route.**
- [ ] **Step 2: Run focused tests and verify failure.**
- [ ] **Step 3: Implement pure map-state generation.**
- [ ] **Step 4: Verify serialization contains only intended fields and rerun tests.**
- [ ] **Step 5: Commit `feat: add God’s Eye in-app map state`.**

### Task 7: Documentation and integration guards

**Files:**
- Modify: `quality_of_life/README.md`
- Modify: `fullstack-agent.md`
- Create: `.github/workflows/jarvis-runtime.yml`
- Modify: `tests/test_quality_of_life_integration.py`

- [ ] **Step 1: Add integration tests that construct the default runtime with fake providers and exercise place search, location, route, screen, clipboard, window, browser, and computer operations through the same dispatcher.**
- [ ] **Step 2: Run the full Python test suite.**
- [ ] **Step 3: Add CI matrix matching the existing Python 3.11/3.12/3.13 Windows+Ubuntu coverage.**
- [ ] **Step 4: Update docs so shipped capabilities are no longer labeled as merely planned and document provider/permission behavior.**
- [ ] **Step 5: Commit `test: cover unified Jarvis runtime integration`.**

### Task 8: Final verification and merge gate

**Files:**
- No source changes unless a test exposes a concrete regression.

- [ ] **Step 1: Inspect all changed files for secret exposure, unrestricted subprocess use, and accidental startup changes.**
- [ ] **Step 2: Run the complete CI suite on the feature branch and inspect every job, not just the workflow summary.**
- [ ] **Step 3: Run repository-wide diff checks against `main` and confirm existing self-coding/voice files are untouched except intended docs.**
- [ ] **Step 4: Open a pull request to `main` with explicit verification evidence and merge only after all required checks are green.**
- [ ] **Step 5: Verify the post-merge `main` commit and post-merge CI are green.**
