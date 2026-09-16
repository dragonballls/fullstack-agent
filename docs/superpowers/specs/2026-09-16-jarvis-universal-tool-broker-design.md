# Jarvis Universal Tool Broker Design

**Goal:** Expand Jarvis from a fixed capability set into a guarded, extensible tool broker that can expose new tool families through one policy-aware interface while preserving deny-by-default execution.

## Scope

The broker will provide a stable internal contract for tool discovery, invocation, capability/risk metadata, and diagnostics. Existing local computer, browser, filesystem, Windows, device, account, location, cloud, and self-coding tools remain the authoritative implementations. New adapters can be registered without changing the planner/runtime contract.

The first expansion adds generic tool families for web research and remote API integrations, with explicit configuration and no secret values returned to model-visible results. The broker will support tool manifests, provider health, capability checks, confirmation requirements, bounded timeouts, redacted errors, and structured results.

## Safety

- Deny by default: every broker operation maps to a declared `Capability` and `OperationRisk`.
- Mutating, external, and destructive operations remain confirmation-gated by the existing policy.
- Credentials are resolved from environment/keyring-backed providers and are never included in result payloads or diagnostics.
- Network destinations are validated against registered provider origins; arbitrary executable commands are not a broker capability.
- Each invocation has a bounded timeout and maximum result size.
- Tool implementations may be disabled independently without removing the core runtime.

## Architecture

`AgentOrchestrator -> JarvisRuntime -> UniversalToolBroker -> ToolAdapter`

`UniversalToolBroker` owns discovery and policy enforcement. Adapters own provider-specific transport. `OperationSpec` remains the canonical operation metadata source, while broker manifests expose machine-readable schemas for planners and diagnostics.

The broker exposes three primitive operations:

- `tools.list`: enumerate currently registered, policy-visible tools.
- `tools.describe`: return a single tool manifest without secrets.
- `tools.invoke`: execute a named operation after capability and confirmation checks.

Built-in adapters:

- `WebToolAdapter`: bounded HTTP GET plus search-provider requests using configured endpoints; read-only.
- `ApiToolAdapter`: allowlisted JSON REST operations for configured external services; mutation operations require confirmation.

The existing runtime keeps direct registrations for mature local tools. The broker becomes the common extensibility path for future adapters and remote connector-backed functionality.

## Verification

Unit tests cover manifest registration, duplicate rejection, capability denial, confirmation enforcement, timeout/error redaction, URL allowlisting, result truncation, and adapter dispatch. Integration tests verify the broker can be created from the existing runtime and that unknown operations cannot execute.

Hosted CI remains the authoritative repository-level verification. Machine-only behaviors such as browser rendering, microphone playback, real account OAuth, and actual Windows mutations still require local validation as already documented by `JARVIS_READINESS.md`.
