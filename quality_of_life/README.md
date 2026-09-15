# Quality of Life

This subsystem is a real capability layer for fullstack-agent. It adds computer awareness, computer interaction, orchestration, background maintenance, cloud-model routing, and God’s Eye location/map context without replacing memory, voice, face, hands, or guarded self-coding.

## Shipped capabilities

- **Windows computer control:** mouse movement/click/scroll, bounded text entry/hotkeys, and explicit application launch.
- **Screen capture:** capability-gated full-screen capture with optional image saving.
- **Clipboard:** bounded text read/write through the platform clipboard.
- **Windows control:** enumerate visible windows and explicitly focus, minimize, maximize, or close a selected window.
- **Browser automation:** optional Playwright control for approved HTTP(S) URLs.
- **Background jobs:** bounded daemon jobs with cancellation and active-job inspection.
- **Cloud routing:** deterministic provider failover with no local LLM requirement.
- **God’s Eye:** place search, current-location context, route generation, and an in-app map-state contract (`surface: gods-eye`).
- **Windows maintenance:** guarded PC diagnostics, identification of eligible idle/high-memory user applications, verified process stopping, reversible user-startup prevention, startup restoration, system-file health scans, and explicitly confirmed repair/network-reset operations.
- **Unified runtime:** `JarvisRuntime.dispatch(...)` is the single capability-aware execution surface for these operations.

## God’s Eye behavior

Location phrases resolve through the runtime to structured place results. For example, an intent such as `open Tokyo` becomes a `gods_eye.search` operation, while `take me to the airport` becomes `gods_eye.route_to`. The runtime can therefore put the result into the God’s Eye map surface instead of treating the place as ordinary chat text.

Current location has two paths: an explicit system/browser/provider callback can supply the permitted location, or the optional IP fallback can supply approximate coordinates when `JARVIS_ALLOW_IP_LOCATION=1`. IP geolocation is deliberately marked approximate (`accuracy_m` = 25000) and is never presented as precise GPS. Without a permitted provider result, God’s Eye reports location as unavailable rather than inventing one.

`gods_eye.route_to` only creates a navigation target and URL; it does not silently launch an external browser. Any browser launch still passes through `BROWSER_CONTROL` and the normal confirmation hook.

## Windows maintenance behavior

Say things like `diagnose my PC`, `what is using my RAM`, `clean up background apps`, or `stop Steam and stop it from starting with Windows`. The maintenance facade produces structured operations and protects Windows/system/security processes, Jarvis/agent processes, the foreground application, and protected system paths. Startup prevention is limited to the current-user Run key so it can be restored. High-risk Windows repairs remain disabled until an explicit confirmation is supplied.

## Safety boundaries

Capabilities are deny-by-default. Mutating operations receive a capability check before execution, and mouse/keyboard/window/app/browser/repository-write/background operations also require caller confirmation. Credentials, browser profiles, private files, and precise location identifiers are not logged by this subsystem. No operation accepts model-provided shell text for execution.

Windows maintenance adds another policy boundary: process termination is limited to verified identities, startup management is restricted to reversible current-user entries, and system/network repair commands are confirmation-gated. A failed check or action is reported without aborting unrelated capabilities.

## Compatibility

The subsystem is optional. Imports remain safe when Windows-only or browser dependencies are absent, and the core God’s Eye contracts are testable without network access. Provider/network failures become empty or unavailable results rather than taking down the base agent.
