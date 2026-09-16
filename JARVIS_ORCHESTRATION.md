# Jarvis multi-AI orchestration

The Jarvis extension layer uses OmniRoute as the cloud model gateway and chooses the smallest sufficient workflow for each request.

## Profiles

- `fast`: one low-latency `auto/fast` request.
- `smart`: `auto/smart` for harder reasoning and independent specialist checks when useful.
- `coding`: `auto/coding` plus independent implementation/test review before synthesis.
- `vision`: vision-oriented context analysis with the available cloud route.
- `maintenance`: independent PC/process analysis followed by a synthesis step and, for supported requests, a deterministic Windows-maintenance action.

## Parallelism

Independent, read-only specialist requests may run concurrently with a bounded worker pool. `JARVIS_OMNIROUTE_MAX_PARALLEL` controls the worker count (default 4; hard cap 8). The fast path does not fan out.

## Safety boundary

Models never execute arbitrary PowerShell or bypass the capability policy. Computer control, browser control, location, clipboard, and Windows mutations continue through the existing runtime dispatch and confirmation gates. Windows diagnostics use a separate read-only `system.diagnostics` capability so diagnosis does not inherit mutation confirmation requirements.

## Provider failures

OmniRoute remains cloud-only. A missing cloud credential, unavailable provider, or malformed response produces a redacted provider diagnostic. Repeated failures temporarily cool down the affected route so a broken provider is not hammered on every request.

## Latency behavior

The orchestration layer emits a local acknowledgement before model work, avoids a second model call for simple requests, parallelizes independent analysis for complex requests, and records end-to-end latency in the result metadata.

## Persistent workflows

Named user workflows are persisted separately from conversational memory. A workflow stores a stable name, ordered capability actions, optional conditions, confirmation requirements, retry policy, and run metadata. Natural-language requests can resolve a saved workflow by name and invoke it through the existing guarded runtime dispatch; workflow execution never bypasses capability policy. Definitions and run history survive process restarts so a workflow created on one day can be invoked on a later day.

## Machine-only verification

Hosted CI can verify routing, concurrency, policy, workflow persistence, and deterministic dispatch contracts. Actual microphone/speaker playback, ElevenLabs speech quality, screen capture, mouse movement, browser launches, camera permission, and Windows repair effects still require validation on the user's Windows machine.
