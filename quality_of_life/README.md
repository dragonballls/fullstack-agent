# Quality of Life

This subsystem is a real capability layer for fullstack-agent. It adds computer awareness, computer interaction, orchestration, background maintenance, cloud-model routing, God’s Eye location/map context, and explicit external-account authorization without replacing memory, voice, face, hands, or guarded self-coding.

## Shipped capabilities

- **Windows computer control:** mouse movement/click/scroll, bounded text entry/hotkeys, and explicit application launch.
- **Webcam hand control:** optional local hand tracking that maps a pointing hand to the pointer and pinch/release to a click through the existing guarded computer controller. A closed fist or explicit stop disables the bridge.
- **Screen capture:** capability-gated full-screen capture with optional image saving.
- **Clipboard:** bounded text read/write through the platform clipboard.
- **Windows control:** enumerate visible windows and explicitly focus, minimize, maximize, or close a selected window.
- **Browser automation:** optional Playwright control for approved HTTP(S) URLs.
- **Background jobs:** bounded daemon jobs with cancellation and active-job inspection.
- **Cloud routing:** deterministic provider failover with no local LLM requirement.
- **God’s Eye:** place search, current-location context, route generation, and an in-app map-state contract (`surface: gods-eye`).
- **Life360 family locations:** an explicitly enabled Home Assistant bridge can expose the user's authorized Life360 Circle members as God’s Eye family markers. Jarvis reads only Home Assistant `device_tracker` entities attributed to Life360 (or an explicit entity allowlist); it does not log into Life360 directly or bypass Circle/location-sharing choices.
- **External account access:** an explicit account registry can hold user-authorized GitHub, Google, YouTube, and generic provider grants. Credentials are resolved at runtime and are never persisted by this layer.
- **GitHub repository integration:** an authorized GitHub grant can request a repository fork through the GitHub API, with write confirmation and token checks.
- **Windows maintenance:** guarded PC diagnostics, identification of eligible idle/high-memory user applications, verified process stopping, reversible user-startup prevention, startup restoration, system-file health scans, and explicitly confirmed repair/network-reset operations.
- **Unified runtime:** `JarvisRuntime.dispatch(...)` is the single capability-aware execution surface for these operations.

## Hand control

The browser tracker uses the existing barehands/MediaPipe approach and sends only normalized coordinates and gesture state to a loopback-only bridge on `127.0.0.1:8795`. The bridge never exposes desktop-control credentials to the browser and is off unless explicitly enabled.

Start the optional bridge with `python -m quality_of_life.hand_control_server --enabled`, then open `http://127.0.0.1:8795/` in a Chromium-based browser and permit camera access. The bridge is intentionally isolated: camera permission failures, tracker loading failures, or browser disconnects do not stop the rest of Jarvis.

## External account behavior

Jarvis can be given access to an account without embedding credentials into the repository. Non-secret grants are configured as structured provider/account/scope data; secrets remain in the machine's secret environment or an OAuth/token broker. A provider operation must match an enabled grant, and every non-read scope requires confirmation unless the calling integration explicitly carries an already-authorized confirmation context.

The GitHub repository client accepts either a GitHub repository URL or `owner/name`, validates the repository identifier, calls the authenticated GitHub API, and returns only the resulting repository metadata. It never writes the token to disk or includes it in returned results.

This layer is deliberately extensible: Google and YouTube account grants describe authorization, while provider-specific adapters are responsible for their APIs and OAuth flows. Granting an account does not imply unrestricted access to every provider operation.

## God’s Eye behavior

Location phrases resolve through the runtime to structured place results. For example, an intent such as `open Tokyo` becomes a `gods_eye.search` operation, while `take me to the airport` becomes a `gods_eye.route_to`. The runtime can therefore put the result into the God’s Eye map surface instead of treating the place as ordinary chat text.

Current location has two paths: an explicit system/browser/provider callback can supply the permitted location, or the optional IP fallback can supply approximate coordinates when `JARVIS_ALLOW_IP_LOCATION=1`. IP geolocation is deliberately marked approximate (`accuracy_m` = 25000) and is never presented as precise GPS. Without a permitted provider result, God’s Eye reports location as unavailable rather than inventing one.

### Life360 / family map

Life360 family data is opt-in and provider-backed. Configure the existing Home Assistant Life360 integration first, then enable the bridge with `JARVIS_LIFE360_ENABLED=1`, `JARVIS_LIFE360_HA_URL`, and `JARVIS_LIFE360_HA_TOKEN`. The bridge reads Home Assistant's authenticated `/api/states` endpoint and normalizes Life360 `device_tracker` attributes such as latitude, longitude, GPS accuracy, battery level, address, place, and last-seen time. Home Assistant's REST API requires a Bearer access token, and its `/api/states` endpoint exposes entity attributes. citeturn631543search0turn193980search1

Jarvis exposes `gods_eye.family_locations`, `gods_eye.family_context`, and `gods_eye.family_map` under the existing `LOCATION_READ` capability. Family location data is never fetched unless Life360 is explicitly enabled and an authorized Home Assistant token is configured. The default transport accepts only localhost/private-IP or `.local` Home Assistant hosts.

`gods_eye.route_to` only creates a navigation target and URL; it does not silently launch an external browser. Any browser launch still passes through `BROWSER_CONTROL` and the normal confirmation hook.

## Windows maintenance behavior

Say things like `diagnose my PC`, `what is using my RAM`, `clean up background apps`, or `stop Steam and stop it from starting with Windows`. The maintenance facade produces structured operations and protects Windows/system/security processes, Jarvis/agent processes, the foreground application, and protected system paths. Startup prevention is limited to the current-user Run key so it can be restored. High-risk Windows repairs remain disabled until an explicit confirmation is supplied.

## Safety boundaries

Capabilities are deny-by-default. Mutating operations receive a capability check before execution, and mouse/keyboard/window/app/browser/repository-write/background operations also require caller confirmation. Credentials, browser profiles, private files, and precise location identifiers are not logged by this subsystem. No operation accepts model-provided shell text for execution.

External account access does not override the capability policy. A connected account is an identity and authorization source, not a bypass around local safety controls. Destructive, financial, or otherwise high-impact provider operations remain confirmation-gated by the same principle.

Windows maintenance adds another policy boundary: process termination is limited to verified identities, startup management is restricted to reversible current-user entries, and system/network repair commands are confirmation-gated. A failed check or action is reported without aborting unrelated capabilities.

## Compatibility

The subsystem is optional. Imports remain safe when Windows-only or browser dependencies are absent, and the core God’s Eye and account-access contracts are testable without network access. Provider/network failures become empty or unavailable results rather than taking down the base agent.
