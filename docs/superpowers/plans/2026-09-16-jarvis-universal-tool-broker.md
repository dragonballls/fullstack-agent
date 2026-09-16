# Jarvis Universal Tool Broker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a guarded Universal Tool Broker so Jarvis can discover and invoke extensible web/API tools through one policy-aware interface while retaining the existing local tool implementations.

**Architecture:** `AgentOrchestrator -> JarvisRuntime -> UniversalToolBroker -> ToolAdapter`. The broker enforces capability/risk policy, confirmation, timeouts, destination allowlists, and redacted structured results; adapters handle provider transport.

**Tech Stack:** Python 3.11–3.13, dataclasses, urllib/http.client-compatible standard-library networking, unittest/pytest-compatible tests, existing `Capability`, `OperationSpec`, `JarvisRuntime`, GitHub Actions release gate.

**Spec:** `docs/superpowers/specs/2026-09-16-jarvis-universal-tool-broker-design.md`

## Global Constraints

- Deny-by-default capability policy remains authoritative.
- Mutating, external, and destructive operations require the existing confirmation boundary.
- Never return credentials, authorization headers, or secret values in model-visible results.
- Network destinations must be registered/allowlisted.
- Arbitrary shell/PowerShell execution is not added as a broker primitive.
- Every new operation is represented in `OperationSpec` and covered by tests.
- Hosted CI must remain green before merge.

---

### Task 1: Define broker contracts and manifests

**Files:**
- Create: `quality_of_life/tool_broker.py`
- Create: `tests/test_tool_broker.py`
- Modify: `quality_of_life/capabilities.py`

**Interfaces:**
- `ToolManifest(name: str, description: str, operations: tuple[str, ...])`
- `ToolAdapter` protocol with `manifest()` and `invoke(operation: str, arguments: dict[str, object])`
- `UniversalToolBroker.register(adapter)`
- `UniversalToolBroker.list_manifests()`
- `UniversalToolBroker.describe(name)`
- `UniversalToolBroker.invoke(operation, arguments, confirmed=False)`

- [ ] **Step 1: Write failing tests for registration and discovery**

```python
class FakeAdapter:
    def manifest(self):
        return ToolManifest("fake", "fake adapter", ("fake.read",))

    def invoke(self, operation, arguments):
        return {"operation": operation, "arguments": arguments}


def test_broker_lists_registered_manifest():
    broker = UniversalToolBroker()
    broker.register(FakeAdapter())
    assert broker.list_manifests() == (ToolManifest("fake", "fake adapter", ("fake.read",)),)
```

- [ ] **Step 2: Run the broker tests to verify the missing symbols fail**

Run: `python -m pytest tests/test_tool_broker.py -q`
Expected: FAIL because `UniversalToolBroker` and `ToolManifest` do not exist yet.

- [ ] **Step 3: Implement the minimal manifest/adapter contract**

```python
@dataclass(frozen=True)
class ToolManifest:
    name: str
    description: str
    operations: tuple[str, ...]

class ToolAdapter(Protocol):
    def manifest(self) -> ToolManifest: ...
    def invoke(self, operation: str, arguments: dict[str, object]) -> object: ...
```

- [ ] **Step 4: Add broker discovery and duplicate protection**

```python
class UniversalToolBroker:
    def __init__(self):
        self._adapters: dict[str, ToolAdapter] = {}

    def register(self, adapter):
        manifest = adapter.manifest()
        if manifest.name in self._adapters:
            raise ValueError(f"tool already registered: {manifest.name}")
        self._adapters[manifest.name] = adapter
```

- [ ] **Step 5: Add `tools.*` operation specs**

Register `tools.list`, `tools.describe`, and `tools.invoke` as read/external operations using existing capability enums, without adding an unrestricted execution capability.

- [ ] **Step 6: Run the targeted tests**

Run: `python -m pytest tests/test_tool_broker.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add quality_of_life/tool_broker.py quality_of_life/capabilities.py tests/test_tool_broker.py
git commit -m "feat: add universal tool broker contracts"
```

### Task 2: Add policy enforcement, confirmations, timeouts, and redaction

**Files:**
- Modify: `quality_of_life/tool_broker.py`
- Modify: `tests/test_tool_broker.py`

**Interfaces:**
- `UniversalToolBroker.invoke(operation, arguments, confirmed=False) -> ToolResult`
- `ToolResult(ok: bool, operation: str, data: object | None = None, error: str | None = None)`

- [ ] **Step 1: Add failing tests for capability denial and confirmation gating**

```python
def test_broker_denies_unallowed_capability():
    broker = UniversalToolBroker(policy=CapabilityPolicy())
    broker.register(FakeAdapter())
    result = broker.invoke("fake.read", {})
    assert not result.ok
    assert "Capability is not enabled" in result.error
```

```python
def test_broker_requires_confirmation_for_mutation():
    # register an adapter whose operation maps to a MUTATE operation
    result = broker.invoke("fake.write", {})
    assert not result.ok
    assert "confirmation required" in result.error
```

- [ ] **Step 2: Run to verify correct red failures**

Run: `python -m pytest tests/test_tool_broker.py -q`
Expected: FAIL at the new behavior assertions.

- [ ] **Step 3: Implement operation-to-adapter lookup and policy checks**

Resolve an operation with `quality_of_life.capabilities.operation()`, map it to the adapter declared by its manifest, call `policy.check(spec.capability)`, and require confirmation when `policy.needs_confirmation(spec.capability)` is true.

- [ ] **Step 4: Add bounded execution and sanitized errors**

Use a daemon worker thread and `concurrent.futures` timeout so an adapter cannot block the runtime indefinitely. Convert transport exceptions to short, secret-safe error strings without including request headers, tokens, or response bodies beyond a bounded diagnostic excerpt.

- [ ] **Step 5: Add result-size truncation**

Ensure strings and JSON-like mappings returned by adapters are capped at a fixed broker limit and marked as truncated rather than allowing unbounded model context growth.

- [ ] **Step 6: Run targeted tests**

Run: `python -m pytest tests/test_tool_broker.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add quality_of_life/tool_broker.py tests/test_tool_broker.py
git commit -m "feat: enforce universal tool policy boundaries"
```

### Task 3: Add allowlisted web adapter

**Files:**
- Create: `quality_of_life/web_tools.py`
- Modify: `quality_of_life/tool_broker.py`
- Modify: `quality_of_life/capabilities.py`
- Create: `tests/test_web_tools.py`

**Interfaces:**
- `WebToolAdapter` manifest with `web.fetch` and `web.search`
- `WebToolAdapter.invoke(operation, arguments)` returns structured, bounded text/metadata.

- [ ] **Step 1: Write failing tests for destination validation and response bounds**

```python
def test_web_adapter_rejects_unregistered_host():
    adapter = WebToolAdapter(allowed_hosts={"example.com"})
    result = adapter.invoke("web.fetch", {"url": "https://not-example.invalid/"})
    assert not result["ok"]
```

```python
def test_web_adapter_truncates_response():
    # inject a transport fixture returning oversized content
    result = adapter._parse_response("x" * 10000)
    assert result["truncated"] is True
```

- [ ] **Step 2: Run to verify red**

Run: `python -m pytest tests/test_web_tools.py -q`
Expected: FAIL before adapter implementation.

- [ ] **Step 3: Implement URL parsing and host allowlisting**

Accept HTTPS URLs only by default, reject credentials embedded in URLs, normalize the hostname, and require it to match an explicit allowlist or a configured suffix entry.

- [ ] **Step 4: Implement bounded fetch**

Use the standard library HTTP client, a connect/read timeout, a maximum body size, and content-type checks for text/JSON. Return status, final URL, headers limited to safe metadata, and bounded body text.

- [ ] **Step 5: Implement configurable search provider transport**

Support a configured JSON search endpoint through environment variables (`JARVIS_WEB_SEARCH_URL`, optional `JARVIS_WEB_SEARCH_API_KEY_ENV`) while never emitting the key. Parse common `{results:[...]}` responses into `{title,url,snippet}` records.

- [ ] **Step 6: Add operation specs and broker registration**

Add `web.fetch` as read-only and `web.search` as read-only, then register `WebToolAdapter` from the default runtime broker.

- [ ] **Step 7: Run tests**

Run: `python -m pytest tests/test_web_tools.py tests/test_tool_broker.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add quality_of_life/web_tools.py quality_of_life/tool_broker.py quality_of_life/capabilities.py tests/test_web_tools.py
git commit -m "feat: add allowlisted web research adapter"
```

### Task 4: Add configured JSON API adapter

**Files:**
- Create: `quality_of_life/api_tools.py`
- Modify: `quality_of_life/tool_broker.py`
- Modify: `quality_of_life/capabilities.py`
- Create: `tests/test_api_tools.py`

**Interfaces:**
- `ApiEndpoint(name, base_url, key_env, allowed_operations)`
- `ApiToolAdapter(endpoints)`
- Operations `api.request.read` and `api.request.write` with endpoint-name routing.

- [ ] **Step 1: Write failing tests for endpoint allowlisting and secret-safe headers**

```python
def test_api_adapter_rejects_unknown_endpoint():
    adapter = ApiToolAdapter(())
    result = adapter.invoke("api.request.read", {"endpoint": "missing", "path": "/v1"})
    assert result["ok"] is False
```

```python
def test_api_adapter_never_returns_api_key():
    # configured fixture endpoint returns an auth-related error
    result = adapter.invoke("api.request.read", {"endpoint": "fixture", "path": "/denied"})
    assert "SECRET" not in str(result)
```

- [ ] **Step 2: Run red tests**

Run: `python -m pytest tests/test_api_tools.py -q`
Expected: FAIL before implementation.

- [ ] **Step 3: Implement endpoint registry**

Require every endpoint to have an HTTPS base URL, an optional environment-variable key name, and an explicit set of relative paths or path prefixes. Reject absolute request URLs and traversal-like paths.

- [ ] **Step 4: Implement GET and JSON request handling**

Resolve keys at call time from environment variables, set standard JSON headers, bound response size and timeout, and normalize JSON/text responses to the same `ToolResult` contract.

- [ ] **Step 5: Gate write requests**

Map `api.request.write` to `Capability.ACCOUNT_WRITE` and require `confirmed=True` through the broker before transport execution.

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_api_tools.py tests/test_tool_broker.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add quality_of_life/api_tools.py quality_of_life/tool_broker.py quality_of_life/capabilities.py tests/test_api_tools.py
git commit -m "feat: add guarded configured API adapter"
```

### Task 5: Integrate broker into JarvisRuntime and planner

**Files:**
- Modify: `quality_of_life/runtime.py`
- Modify: `quality_of_life/manifest.py`
- Modify: `quality_of_life/planner.py`
- Create: `tests/test_universal_runtime.py`

**Interfaces:**
- `JarvisRuntime.tool_broker()` returns a singleton `UniversalToolBroker`.
- Planner can express `tools.list`, `tools.describe`, `web.search`, and `web.fetch`.
- Existing direct capability dispatch remains unchanged for mature tools.

- [ ] **Step 1: Write failing runtime integration tests**

```python
def test_runtime_exposes_universal_tool_broker():
    runtime = JarvisRuntime(CapabilityPolicy(allowed=frozenset({Capability.FILE_READ})))
    assert runtime.tool_broker().list_manifests()
```

- [ ] **Step 2: Run red**

Run: `python -m pytest tests/test_universal_runtime.py -q`
Expected: FAIL because `tool_broker()` is absent.

- [ ] **Step 3: Implement lazy broker construction**

Construct one broker per runtime, pass the same policy object used by `QoLOrchestrator`, and register built-in web/API adapters only when their required configuration is present.

- [ ] **Step 4: Add broker tool to the manifest registry**

Register `tool_broker` as a lazy tool while leaving existing tools intact.

- [ ] **Step 5: Add planner allowlist entries**

Permit the broker-safe operations and keep all arbitrary shell/executable-path language prohibited by the planner prompt.

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_universal_runtime.py tests/test_planner.py tests/test_tool_broker.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add quality_of_life/runtime.py quality_of_life/manifest.py quality_of_life/planner.py tests/test_universal_runtime.py
git commit -m "feat: integrate universal tool broker into runtime"
```

### Task 6: Add self-coding capability discovery contract

**Files:**
- Modify: `self_coding/agent.py`
- Modify: `tests/test_self_coding.py`
- Modify: `JARVIS_READINESS.md`

**Interfaces:**
- `SelfCodingAgent.inspect_tool_gap(goal: str) -> ToolGap | None`
- `SelfCodingAgent.propose_tool_extension(goal: str, gap: ToolGap) -> str`
- Proposed extensions are repository changes only; activation remains gated by tests and broker policy.

- [ ] **Step 1: Write failing tests**

```python
def test_self_coding_detects_missing_broker_capability():
    agent = build_agent()
    gap = agent.inspect_tool_gap("research a site not supported by configured adapters")
    assert gap is not None
    assert gap.kind == "tool_capability"
```

- [ ] **Step 2: Run red**

Run: `python -m pytest tests/test_self_coding.py -q`
Expected: FAIL because the discovery contract is absent.

- [ ] **Step 3: Implement deterministic gap extraction**

Identify missing tool-family requirements from a constrained set of structured planner errors; do not let natural-language model output bypass the capability catalog.

- [ ] **Step 4: Implement proposal output**

Return a structured repository task containing the desired operation name, required capability/risk, adapter file target, required tests, and verification command.

- [ ] **Step 5: Add readiness diagnostics**

Document that self-expansion is code generation plus verification, not automatic permission escalation or arbitrary execution.

- [ ] **Step 6: Run self-coding tests**

Run: `python -m pytest tests/test_self_coding.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add self_coding/agent.py tests/test_self_coding.py JARVIS_READINESS.md
git commit -m "feat: teach self-coding to identify tool capability gaps"
```

### Task 7: Full verification and release

**Files:**
- Modify: `README.md` or `JARVIS_ORCHESTRATION.md` only if verification discovers documentation drift.

- [ ] **Step 1: Run the complete relevant local test suite**

Run: `python -m pytest tests/test_tool_broker.py tests/test_web_tools.py tests/test_api_tools.py tests/test_universal_runtime.py tests/test_planner.py tests/test_self_coding.py -q`
Expected: PASS with zero failures.

- [ ] **Step 2: Review changed code for secret leakage and policy bypasses**

Search for direct process spawning, unrestricted URLs, secret-value logging, confirmation bypasses, and any broker route that lacks an `OperationSpec` mapping.

- [ ] **Step 3: Push the branch and open a pull request**

Create PR from `feature/jarvis-universal-tool-broker` to `main` with the design, tests, and known machine-only limitations summarized.

- [ ] **Step 4: Wait for and inspect all required CI checks**

The merge gate is not complete until self-coding safety, integration, quality-of-life, Windows maintenance, and the full Jarvis release gate are successful on the proposed head.

- [ ] **Step 5: Fix any CI failure using a fresh failing test before production changes**

Do not merge red CI. Preserve the deny-by-default boundary when correcting failures.

- [ ] **Step 6: Merge only after all required checks are green**

Use the repository's normal merge path, then verify the post-merge workflows on the resulting `main` commit.
