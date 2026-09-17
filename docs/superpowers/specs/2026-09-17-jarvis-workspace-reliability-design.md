# Jarvis Workspace and Reliability Design

**Repository:** `dragonballls/fullstack-agent`  
**Branch:** `feat/jarvis-advanced-workspace`  
**Status:** Design approved in chat; written spec for review

## Goal

Turn the current persistent Jarvis workspace shell into a reliable, guarded agent surface that adds useful workspace visibility and activity handling without replacing or weakening existing Jarvis systems.

## Non-Negotiable Compatibility Rules

1. The existing `JarvisWebApi` contract remains intact; the workspace API extends it rather than replacing existing methods.
2. The persistent command input remains available in every workspace.
3. The existing visualizer remains the underlying visual/voice interaction surface; the workspace overlay must not capture unrelated visualizer input.
4. Voice, hands, self-coding, permissions, runtime dispatch, updater, authentication, backend APIs, and existing device/location providers keep their existing safety gates.
5. Location data is shown only when the existing guarded location capability succeeds. The UI must never fabricate a current device or family location.
6. Optional integrations fail independently and leave the base Jarvis command surface usable.
7. No feature may silently broaden a capability policy or bypass confirmation requirements.
8. Windows remains the primary packaged target and the existing no-console desktop entrypoint remains usable.

## Architecture

The workspace is a presentation and orchestration layer over existing Jarvis capabilities. It does not own device control, location providers, browser automation, coding execution, or system mutation. Instead, each surface reads from narrow adapters and the existing guarded runtime.

The next layer is a shared activity contract. Long-running operations publish structured activity state that the workspace can render. The activity layer is observational and cancellation-aware; it does not grant permissions and does not execute tools on its own.

God's Eye is a guarded visualization surface. It can render the current authorized location result and expose provider state, but it must treat phone/family feeds as separate provider sources. A future Life360 connector, if enabled and authenticated, must implement the provider interface instead of being special-cased into the workspace.

## Workspace Contract

Supported workspace identifiers are:

- `home`
- `gods-eye`
- `coding`
- `browser`
- `system`
- `workflows`

Every workspace state includes:

- active workspace
- visible command bar state
- input mode
- ordered panel identifiers

Activation is deterministic. Unknown workspace identifiers are rejected with a controlled `ValueError` at the bridge boundary and do not mutate the prior state.

## Activity Contract

Introduce a small typed activity model with these semantics:

- `queued`: accepted but not executing
- `running`: currently executing
- `waiting`: blocked on an external input or confirmation
- `succeeded`: completed successfully
- `failed`: completed with an error
- `cancelled`: intentionally stopped

Each activity record contains a stable identifier, human-readable title, status, optional progress percentage, current step text, timestamps, and a non-sensitive error summary when applicable.

The activity store must be bounded so stale entries cannot grow without limit. It is process-local and does not become a new persistence/security boundary.

Cancellation is cooperative. A caller may request cancellation, and an activity transitions to `cancelled` only when its execution layer acknowledges the request. The activity layer must not kill arbitrary processes merely to force a state transition.

## Workspace Integration

Home shows readiness and active activity information.

God's Eye shows:

- map/context panel
- entity/provider state
- activity panel
- command surface
- explicit authorization/provider availability state

Coding shows active coding activity without taking ownership of the existing self-coding engine.

Browser shows active browser activity without replacing the existing browser integration.

System shows health/process activity without bypassing existing maintenance guards.

Workflows shows queued/running/completed workflow activity while preserving the existing workflow engine.

All workspace actions must degrade gracefully if their backing subsystem is unavailable.

## God's Eye Provider Boundary

Location rendering consumes provider-neutral results. The first supported provider is the existing guarded `location.read` runtime action (`locations.current`).

Provider slots must distinguish at least:

- current device location
- connected phone location
- shared family location

Unavailable providers are rendered as unavailable rather than inferred. A provider may expose its authorization status and last-known metadata, but the UI must not imply live tracking unless the provider explicitly reports a live/authorized feed.

No direct Life360 behavior is added as a fake implementation. A real connector must authenticate through its supported provider interface and map its data into the provider-neutral contract.

## Error Isolation

Failures in voice, visualizer, browser, location, hands, updater, activity rendering, or optional providers must be contained at their boundary.

The native desktop host must continue to initialize the command bar even when an optional integration raises during initialization. Errors are logged through the existing logging path without leaking secrets.

Workspace API methods return structured availability/status results for expected optional failures rather than raising across the JavaScript boundary. Invalid workspace input remains a programmer-facing validation error.

## Security and Privacy

The existing deny-by-default `CapabilityPolicy` remains authoritative.

Workspace code may request capabilities through the existing runtime. It may not call platform APIs that bypass the runtime for protected data.

Location output is minimized to what the existing provider already authorizes. Error messages exposed to the UI use exception type or sanitized status text rather than raw secrets, tokens, paths containing credentials, or provider responses containing sensitive fields.

## Testing Strategy

Tests are required at four levels.

### Unit and contract tests

Cover:

- workspace state defaults and activation
- invalid workspace handling
- activity lifecycle transitions
- bounded activity storage
- cancellation acknowledgement semantics
- provider result normalization
- provider unavailable/error states
- God's Eye capability dispatch
- privacy-safe failure messages
- command surface preservation
- visualizer pointer/input transparency

### Integration tests

Exercise workspace API installation against the real desktop API shape and the guarded runtime adapter with fakes for optional providers. Confirm optional failure does not remove the command surface.

### Native Windows smoke tests

The packaged `Jarvis.exe` must:

1. launch without a console window
2. start the expected local services
3. expose the existing command bar
4. render the workspace shell
5. retain visualizer availability
6. tolerate unavailable optional providers
7. exit cleanly under the existing smoke-test mechanism

### Release gates

The existing release workflow must continue to run its regression matrix, compile checks, full unit suite, native Windows build, embedded visualizer smoke test, packaged native host smoke test, artifact publication, and attestation verification.

No release-ready claim is allowed until the latest head has all required GitHub Actions checks green and the published artifact is verified.

## Acceptance Criteria

The implementation is accepted only when all of the following are true:

1. Existing complete test suites remain green.
2. New workspace/activity/provider tests are green.
3. Existing visualizer interaction is not blocked by workspace presentation elements.
4. Existing command input is present in every workspace.
5. God's Eye never fabricates a location and uses the existing guarded location action.
6. Optional integrations can fail without taking down Jarvis' command surface.
7. The packaged Windows executable builds and passes its native smoke test.
8. Release artifact provenance attestation is generated and successfully verified before publication.
9. No existing capability policy or confirmation gate is weakened.
10. The release workflow is green for the exact commit being declared ready.

## Out of Scope for This Change

- inventing or simulating Life360 credentials or live family locations
- bypassing provider authorization
- replacing the existing self-coding engine
- replacing the existing visualizer with a new standalone UI runtime
- adding arbitrary autonomous destructive system maintenance
- claiming software is mathematically bug-free

## Decomposition

Implementation is divided into independently testable units:

1. workspace/activity contracts and UI integration
2. guarded location/provider adapter surface
3. failure isolation and startup resilience
4. comprehensive regression and packaged Windows verification

Each unit must preserve the acceptance criteria above before the next unit is treated as integrated.
