# Jarvis Accounts & Services Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing scoped account-grant foundation into a safe multi-account service layer that can authorize Google, Microsoft, GitHub, YouTube, Instagram-compatible APIs, and browser-only services without making credentials part of Jarvis's brain or bypassing existing policy.

**Architecture:** Keep `AccountAccessRegistry` as the authorization source of truth, add a separate service catalog and OAuth/token-broker interface, and resolve one explicit account identity per action. Provider adapters use official HTTPS APIs where supported; browser automation remains a bounded fallback for services that do not expose the requested API capability. No provider becomes an alternate AI brain.

**Tech Stack:** Python 3.11-3.13, standard library OAuth/HTTP contracts, existing `quality_of_life` capability policy, existing browser controller, unittest/pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-15-full-jarvis-integration-design.md`

## Global Constraints

- Account credentials and OAuth tokens are never written to tracked files, logs, prompts, or model-visible results.
- Multiple identities per provider must be supported without overwriting another identity.
- Read actions may be allowed by an account grant; write, destructive, financial, and security-sensitive actions require confirmation by default.
- OAuth authorization must be explicit user consent; Jarvis never requests or stores account passwords.
- Provider API access and browser fallback both remain behind existing capability/permission checks.
- OmniRoute remains the only model-routing/brain path; service accounts are tools/resources only.
- Missing provider credentials, revoked consent, unsupported scopes, or provider outages must fail closed with redacted diagnostics.
- Existing QOL, self-coding, integration, hand-control, location, and Windows-maintenance behavior must remain unchanged.
- Hosted CI can verify contracts and mocks but cannot certify real third-party account access or a user's browser login/session.

---

### Task 1: Expand account/provider identity contracts

**Files:**
- Create: `quality_of_life/account_integrations.py`
- Modify: `quality_of_life/account_access.py`
- Test: `tests/test_account_integrations.py`

**Interfaces:**
- `ServiceProvider` enum includes `GOOGLE`, `MICROSOFT`, `GITHUB`, `YOUTUBE`, `INSTAGRAM`, `GENERIC_WEB`.
- `AccountIdentity(provider, account_id, label)` identifies one connected account without containing secrets.
- `OAuthClientConfig(provider, authorization_url, token_url, scopes)` describes a provider flow.
- `AccountSelector.select(provider, account_id=None, label=None)` chooses one authorized identity deterministically.

- [ ] **Step 1: Write failing tests**

```python
from quality_of_life.account_integrations import AccountIdentity, AccountSelector, ServiceProvider


def test_multiple_accounts_are_selectable_without_collision():
    accounts = (
        AccountIdentity(ServiceProvider.GOOGLE, "g1", "Personal Google"),
        AccountIdentity(ServiceProvider.GOOGLE, "g2", "Work Google"),
    )
    selector = AccountSelector(accounts)
    assert selector.select(ServiceProvider.GOOGLE, label="Work Google").account_id == "g2"


def test_unknown_identity_is_rejected():
    selector = AccountSelector(())
    with pytest.raises(Exception, match="account"):
        selector.select(ServiceProvider.MICROSOFT, account_id="missing")
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `python -m pytest tests/test_account_integrations.py -v`
Expected: FAIL because the module/interfaces are absent.

- [ ] **Step 3: Implement the immutable identity/catalog interfaces**

Do not store tokens in these dataclasses. Provider enum aliases may map YouTube to Google authentication while retaining YouTube as a service surface.

- [ ] **Step 4: Run focused tests and commit**

Run: `python -m pytest tests/test_account_integrations.py -v`
Expected: PASS.

Commit: `feat: add multi-account service identity contracts`

---

### Task 2: Add secure OAuth/token-broker boundary

**Files:**
- Modify: `quality_of_life/account_integrations.py`
- Test: `tests/test_account_integrations.py`

**Interfaces:**
- `TokenBroker.get_access_token(identity, required_scope) -> str`.
- `TokenBroker.store_refresh_token(...) -> None` is implemented by an external credential store adapter, never by repository JSON.
- `OAuthAuthorizer.authorization_request(provider, state) -> str` returns an authorization URL without secrets.
- `OAuthAuthorizer.exchange_code(code, state)` returns an opaque token-broker handle, never raw tokens to the model.

- [ ] **Step 1: Write failing tests for secret-safe behavior**

Verify URLs contain no client secret, results do not expose tokens, and an unconfigured broker raises a typed configuration error.

- [ ] **Step 2: Run focused tests and verify the failures are limited to new OAuth contracts**

- [ ] **Step 3: Implement provider configuration templates**

Include documented authorization/token endpoints for Google and Microsoft, plus a Google-authenticated YouTube service configuration. Use placeholders for user-supplied client IDs; never put client secrets in code or tests.

- [ ] **Step 4: Add revocation/expiry states**

Return typed `AuthorizationState` values such as `CONNECTED`, `NEEDS_REAUTH`, `DISABLED`, and `UNCONFIGURED`; do not retry revoked tokens indefinitely.

- [ ] **Step 5: Run tests and commit**

Commit: `feat: add secret-safe oauth token boundary`

---

### Task 3: Add provider/service capability catalog

**Files:**
- Modify: `quality_of_life/capabilities.py`
- Modify: `quality_of_life/permissions.py` only if an account-service capability is missing
- Modify: `quality_of_life/manifest.py`
- Test: `tests/test_account_integrations.py`

**Interfaces:**
- `ServiceOperation(name, provider, scope, risk, description)`.
- `service_operation(name)` lookup.
- Registry names include account connection/listing and representative provider operations.

- [ ] **Step 1: Write failing catalog tests**

Cover representative operations such as Google Mail/Calendar/Drive reads, Microsoft Mail/Calendar/OneDrive reads, YouTube channel/video management, GitHub repository actions, and an Instagram/web-browser action that remains capability-gated.

- [ ] **Step 2: Run focused catalog tests and verify failure**

- [ ] **Step 3: Add the catalog without changing existing operation semantics**

Map all writes to `ACCOUNT_WRITE` and reads to `ACCOUNT_READ`; higher-risk operations remain confirmation-gated.

- [ ] **Step 4: Add lazy account-services registry exposure**

The tool must import without making network calls.

- [ ] **Step 5: Run the account and universal integration tests**

Commit: `feat: catalog external account service operations`

---

### Task 4: Implement provider API adapter interfaces and browser fallback

**Files:**
- Create: `quality_of_life/service_adapters.py`
- Modify: `quality_of_life/account_integrations.py`
- Test: `tests/test_service_adapters.py`

**Interfaces:**
- `ServiceAdapter.execute(operation, identity, payload, confirmed=False) -> ServiceResult`.
- `GoogleAdapter`, `MicrosoftAdapter`, `GitHubAdapter`, `YouTubeAdapter`, and `BrowserServiceAdapter` implement the interface.

- [ ] **Step 1: Write failing mocked-transport tests**

No test may call a real provider. Test that adapters attach OAuth bearer tokens supplied by `TokenBroker` and never return the token.

- [ ] **Step 2: Implement read-only API skeletons**

Provide narrowly scoped endpoints for common read operations and typed unsupported-operation responses. Do not claim an operation is supported unless the provider adapter implements it.

- [ ] **Step 3: Implement bounded browser fallback**

Use the existing browser controller only for explicitly authorized domains and operations. Never use stored browser cookies/session state as a hidden credential path; the user must have an authorized browser session and the browser capability must be enabled.

- [ ] **Step 4: Add confirmation enforcement**

Adapters call `AccountAccessRegistry.require(...)` before mutation and honor `confirmed=False` by default.

- [ ] **Step 5: Run adapter tests and commit**

Commit: `feat: add guarded external service adapters`

---

### Task 5: Add account connection and multi-account runtime operations

**Files:**
- Modify: `quality_of_life/runtime.py`
- Modify: `quality_of_life/agent_orchestrator.py`
- Modify: `quality_of_life/manifest.py`
- Test: `tests/test_account_runtime.py`

**Interfaces:**
- `JarvisRuntime.connect_account(provider, label)` returns a user-action authorization URL/status object.
- `JarvisRuntime.list_accounts(provider=None)` returns non-secret identity metadata.
- `JarvisRuntime.select_account(provider, account_id=None, label=None)` returns an identity.
- `JarvisRuntime.service_action(operation, provider, account_id, payload, confirmed=False)` dispatches through the existing capability and confirmation layers.

- [ ] **Step 1: Write failing runtime tests**

Cover multiple Google/Microsoft identities, account selection by label, denied account-write operations, and provider outage handling.

- [ ] **Step 2: Implement lazy runtime registration**

Do not change existing `dispatch`/`handle_text` semantics. Add account-service methods alongside them.

- [ ] **Step 3: Add natural-language intent hooks**

Recognize forms such as `connect my work Microsoft account`, `use my personal Google account`, and `show my YouTube channel`. Do not infer which account to use when more than one matching identity exists.

- [ ] **Step 4: Run full QOL tests and commit**

Commit: `feat: expose guarded multi-account actions through Jarvis runtime`

---

### Task 6: Documentation, readiness, and CI regression gates

**Files:**
- Modify: `quality_of_life/README.md`
- Modify: `README.md`
- Modify: `JARVIS_READINESS.md`
- Create: `tests/test_accounts_ci_contract.py`

- [ ] **Step 1: Add documentation tests first**

Require explicit statements that accounts are OAuth-authorized, credentials are not persisted by the repository, multiple identities are supported, and mutations require confirmation.

- [ ] **Step 2: Document provider setup boundaries**

State exactly which pieces are API-backed, which require user-created OAuth application credentials, and which can fall back to browser control. Do not advertise universal API support where a provider does not offer it.

- [ ] **Step 3: Run the complete existing CI-equivalent suite**

Run the full QOL, integration, self-coding, and Windows-maintenance tests where supported by CI.

- [ ] **Step 4: Open a PR from `feature/jarvis-accounts-services` and do not merge while any required check is pending or failing.**

Commit: `docs: document Jarvis account and service integrations`
