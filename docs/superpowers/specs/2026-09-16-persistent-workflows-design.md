# Persistent Named Workflows for Jarvis

## Status
Approved direction for implementation on `feature/persistent-workflows`.

## Goal
Add a persistent, named workflow system so Jarvis can save multi-step task routines, resolve them by name on later days/restarts, and execute each action through the existing capability and confirmation boundaries.

## Scope
The first release supports user-invoked named workflows. It does not add clock-based scheduling, background autonomous execution, or a second unrestricted command executor.

A workflow contains:
- stable identifier and user-facing name
- normalized aliases for natural-language matching
- ordered action steps
- optional per-step condition metadata limited to supported checks
- created/updated timestamps
- last-run summary
- enabled/disabled state

Each step stores a typed Jarvis operation name plus JSON-compatible arguments. Execution uses the existing `JarvisRuntime.dispatch(...)` surface, so capability checks and confirmation hooks remain authoritative.

## Persistence
Use a small local JSON store, following the repository's existing persistent-store style. The default location is under the user's Jarvis data directory (`~/.jarvis/workflows.json` in non-Windows development environments). An environment override (`JARVIS_WORKFLOW_STORE`) is supported for tests and packaging environments.

Writes are atomic: write a temporary file beside the store and replace the destination only after the serialized document is complete. Malformed or non-object store data is rejected rather than silently overwritten.

No secrets, access tokens, browser profiles, or raw credentials are stored in workflow definitions.

## Workflow model
A step is represented as:

```text
WorkflowStep:
  operation: string
  arguments: dict[str, JSON-compatible value]
  continue_on_error: bool = false
```

A workflow is represented as:

```text
Workflow:
  id: string
  name: string
  aliases: tuple[string, ...]
  steps: tuple[WorkflowStep, ...]
  enabled: bool = true
  created_at: string
  updated_at: string
  last_run: WorkflowRunSummary | None
```

`WorkflowRunSummary` records run id, start/end timestamps, success, completed step count, and redacted error strings. It must never persist sensitive operation arguments or tool-return secrets.

Validation rejects empty names, empty workflows, duplicate step operation names where not meaningful only when explicitly prohibited by operation semantics, unknown operations, malformed arguments, and unsafe filesystem paths embedded in workflow persistence metadata. Operation capability/risk metadata comes from the existing catalog rather than being duplicated into the workflow store.

## Creation and editing
Jarvis adds an explicit workflow service with methods for create, replace, delete, get, list, resolve, and record-run-result. Natural-language creation is intentionally conservative: the first implementation accepts an already structured set of steps from callers/tests and exposes runtime hooks for a later conversational "remember this as ..." feature without inventing a new model protocol in this change.

## Invocation
Natural-language requests are checked before ordinary chat/orchestration handling. Recognized forms include:
- `run my <name>`
- `do my <name>`
- `run <name>`
- `do <name>`
- `start <name>`

Matching uses normalized exact name/alias comparison with deterministic ambiguity handling. A missing or ambiguous workflow falls through to normal chat instead of guessing.

When a workflow resolves, the agent executes its ordered steps through the runtime. Each step receives the same confirmation context supplied to the normal request. A mutating workflow therefore cannot bypass the existing confirmation requirement merely because it was saved earlier.

Default failure behavior is fail-fast. A step may opt into `continue_on_error` only for a workflow whose stored definition explicitly contains that value. The final run result reports completed steps and the first/collected errors without claiming success when any required step failed.

## Runtime integration
Add a workflow tool/service to the existing quality-of-life registry and runtime factory. Add a workflow operation handler in the agent orchestration layer before typed-plan execution so a resolved workflow becomes authoritative deterministic context. Existing ordinary requests must behave exactly as before when no workflow name matches.

Do not modify capability meanings or weaken `CapabilityPolicy`. Do not execute raw shell/PowerShell strings from stored workflows. Workflow steps reference cataloged operation names only.

## Error handling and recovery
- Store corruption: return a safe diagnostic and leave the current process running.
- Unknown operation: reject workflow at save time and again validate at execution time.
- Missing capability: stop before executing that step and mark the run failed.
- Confirmation missing/denied: stop before that mutating step and mark the run as needing confirmation rather than failed due to an internal error.
- Tool exception: record a redacted error and stop unless `continue_on_error` is enabled.
- Partial completion: persisted summary records the exact number of completed steps; no false success response.

## Compatibility and performance
The feature is optional and lazy. Importing Jarvis must not require additional third-party packages. Workflow storage is local-only and uses bounded JSON. The normal chat path should perform at most one inexpensive name-resolution pass when workflows exist.

No UI redesign is part of this change. The existing Fullstack presentation, voice bridge, hands, auto-update, and packaged startup remain untouched except for importing/constructing the workflow service through existing runtime boundaries.

## Testing
Use TDD. Tests cover:
1. model/store round-trip persistence across separate store instances
2. normalized names and aliases
3. atomic writes and malformed-store rejection
4. workflow validation and unknown-operation rejection
5. exact/alias resolution and ambiguity handling
6. fail-fast execution
7. `continue_on_error` execution
8. capability denial and confirmation behavior through `JarvisRuntime.dispatch`
9. deterministic run summaries without secret argument persistence
10. agent-orchestrator integration for recognized and unrecognized workflow requests
11. regression coverage proving ordinary requests retain existing behavior

The complete regression suite, module compilation, and the Windows release gate must pass before merging. The existing packaged visualizer smoke-test failure is a separate issue and must not be declared fixed by this feature unless its own verification passes.
