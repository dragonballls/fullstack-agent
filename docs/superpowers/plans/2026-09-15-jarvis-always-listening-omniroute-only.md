# Jarvis Always-Listening + OmniRoute-Only Voice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Jarvis always listen locally, respond only after hearing the wake word "Jarvis", and make OmniRoute the only supported agent brain without requiring Claude Code.

**Architecture:** Add a small, dependency-light local activation gate with deterministic configuration and single-session locking. Keep brain routing separate: accepted utterances must enter the existing OmniRoute route, while Claude-specific setup is removed from required install/readiness text and guarded by a permanently-disabled Jarvis configuration flag.

**Tech Stack:** Python 3, unittest/pytest-compatible tests, existing `quality_of_life` package, existing OmniRoute HTTP client, Markdown contracts.

**Spec:** docs/superpowers/specs/2026-09-15-jarvis-always-listening-omniroute-design.md

## Global Constraints

- Wake-word processing is local-only and ambient audio is never sent to a cloud provider before wake acceptance.
- OmniRoute is the only conversational/agent provider; Claude Code and Claude subscriptions are not required.
- `JARVIS_ALLOW_CLAUDE=false` is the fixed Jarvis production contract.
- Existing tools, permissions, confirmation paths, self-coding, hand control, locations, God’s Eye, and maintenance remain unchanged.
- The listener fails closed and prevents duplicate active voice sessions.
- Do not log ambient audio, non-addressed transcripts, secrets, or credentials.

### Task 1: Add deterministic voice-activation gate

**Files:**
- Create: `quality_of_life/voice_activation.py`
- Test: `tests/test_voice_activation.py`

**Interfaces:**
- Produces `VoiceActivationConfig.from_env() -> VoiceActivationConfig`.
- Produces `WakeDecision(accepted: bool, confidence: float, phrase: str)`.
- Produces `WakeWordGate.evaluate(transcript: str, confidence: float) -> WakeDecision`.
- Produces `VoiceSessionLock.acquire() -> bool` and `release() -> None`.

- [ ] **Step 1: Write failing tests** for defaults, normalization, confidence threshold, exact wake-word boundary, rejected ambient speech, post-wake timeout, and duplicate lock acquisition.
- [ ] **Step 2: Run `python -m pytest tests/test_voice_activation.py -q` and confirm failure because the module is absent.
- [ ] **Step 3: Implement the minimal gate.** Normalize case/whitespace, require the configured wake word as a token, clamp confidence to [0,1], default to 0.70, and expose a monotonic post-wake deadline. Use a process-local lock plus unique session token so only one listener can own the active session.
- [ ] **Step 4: Run the focused tests and require all pass.
- [ ] **Step 5: Commit `feat: add local Jarvis wake-word gate`.

### Task 2: Enforce OmniRoute-only brain selection

**Files:**
- Modify: `quality_of_life/router.py`
- Test: `tests/test_multi_ai_orchestration.py`
- Create: `tests/test_omniroute_only_contract.py`

**Interfaces:**
- `CloudModelRouter.omniroute_target()` remains the brain target constructor.
- New `CloudModelRouter.jarvis_brain_target(profile)` returns only the OmniRoute target and raises a clear configuration error if OmniRoute is unavailable.

- [ ] **Step 1: Write failing tests** proving Jarvis brain selection yields `omniroute` and never a Claude target, and proving missing OmniRoute configuration fails closed.
- [ ] **Step 2: Run the focused tests and confirm failure.
- [ ] **Step 3: Implement `jarvis_brain_target` without changing generic multi-provider routing used by existing callers. It must use the existing profile model mapping and local OmniRoute endpoint/key environment contract.
- [ ] **Step 4: Run orchestration and contract tests; require all pass.
- [ ] **Step 5: Commit `feat: enforce OmniRoute-only Jarvis brain`.

### Task 3: Remove Claude from required setup/readiness contracts

**Files:**
- Modify: `README.md`
- Modify: `fullstack-agent.md`
- Modify: `JARVIS_READINESS.md`
- Modify: `JARVIS_ORCHESTRATION.md`
- Modify: `tests/test_voice_contract.py`
- Create: `tests/test_no_claude_dependency.py`

**Interfaces:**
- Documentation must describe OmniRoute as Jarvis's required brain path.
- Required install/readiness instructions must not require Claude Code or a Claude subscription.
- Legacy Claude references, if retained, must be explicitly optional/non-Jarvis and must not be startup prerequisites.

- [ ] **Step 1: Add failing contract tests** that assert required setup/readiness text contains no Claude requirement and explicitly documents OmniRoute-only Jarvis operation.
- [ ] **Step 2: Run the focused contract tests and confirm failure.
- [ ] **Step 3: Rewrite only the conflicting requirements. Remove `claude "set me up"` as the Jarvis setup entry point, replace required brain language with OmniRoute, and describe Claude as unsupported for the Jarvis profile rather than a required service.
- [ ] **Step 4: Run `python -m pytest tests/test_voice_contract.py tests/test_no_claude_dependency.py -q` and require all pass.
- [ ] **Step 5: Commit `docs: make Jarvis setup Claude-free`.

### Task 4: Define always-listening Jarvis voice contract

**Files:**
- Modify: `JARVIS_VOICE.md`
- Modify: `tests/test_voice_contract.py`

**Interfaces:**
- Document `JARVIS_VOICE_MODE=open`, `JARVIS_WAKE_WORD=jarvis`, `JARVIS_WAKE_CONFIDENCE=0.70`, `JARVIS_WAKE_POST_WINDOW_SECONDS=6`, and `JARVIS_VOICE_BRAIN=omniroute`.
- Document that ambient audio is locally gated, accepted utterances use OmniRoute, and only one active session is allowed.
- Keep ElevenLabs/Kokoro as speech-output engines rather than brains.

- [ ] **Step 1: Add failing contract assertions for open listening, wake word, local-only gating, OmniRoute brain, and single-session behavior.
- [ ] **Step 2: Run the focused test and confirm failure.
- [ ] **Step 3: Update the voice contract without removing the existing ElevenLabs security rules.
- [ ] **Step 4: Run the focused test and require pass.
- [ ] **Step 5: Commit `docs: define always-listening Jarvis voice contract`.

### Task 5: Add startup/readiness checks for the new voice path

**Files:**
- Modify: `quality_of_life/readiness.py`
- Test: `tests/test_readiness.py`
- Test: `tests/test_universal_integration.py`

**Interfaces:**
- Readiness reports whether local voice activation is configured and whether the OmniRoute brain contract is satisfied.
- Readiness never reports Claude availability as a Jarvis prerequisite.

- [ ] **Step 1: Add failing tests** for healthy OmniRoute/open-listening readiness and clear failure when the required OmniRoute configuration is absent.
- [ ] **Step 2: Run focused readiness tests and confirm failure.
- [ ] **Step 3: Implement the checks using existing environment-resolution patterns and do not perform network calls during basic readiness evaluation.
- [ ] **Step 4: Run readiness + integration tests and require pass.
- [ ] **Step 5: Commit `feat: add Jarvis voice readiness checks`.

### Task 6: Full regression and CI verification

**Files:**
- No production-file changes expected unless a regression is discovered.
- Tests exercised: all existing `tests/`, plus `quality_of_life` matrix and Windows maintenance workflows.

- [ ] **Step 1: Run the full local test suite and Python compile checks.
- [ ] **Step 2: If a failure appears, identify whether it is caused by this change; fix only the minimal related defect and rerun the relevant test before continuing.
- [ ] **Step 3: Open a PR from `feature/jarvis-always-listening-omniroute-only` to `main`.
- [ ] **Step 4: Wait for integration, self-coding, quality-of-life, and Windows-maintenance checks; inspect every job, not only the overall run result.
- [ ] **Step 5: Merge only after every required check is completed successfully.
- [ ] **Step 6: Re-check the post-merge main-branch runs and report the exact commit and green job counts. Do not claim 100% until all required post-merge gates are complete.
