# Jarvis quality floor and quality ladder

Jarvis now treats quality as a versioned product contract rather than a one-time test result.

## One-way floor

The checked-in `quality_floor.json` defines the minimum verified contract. CI compares that manifest with the previous commit when a baseline is available.

A change may keep the floor the same or make it stricter. It is rejected when it:

- lowers the product/UI quality level;
- removes a protected UI build requirement;
- removes required source/test contracts;
- loosens a performance budget; or
- ships a UI build below the verified UI floor.

This applies both to normal release CI and to the self-coding verifier.

## UI quality ladder

| Level | Meaning |
| --- | --- |
| Q1 — Foundation | Basic presentation contract exists. |
| Q2 — Protected | Safe storage and recovery boundaries are present. |
| Q3 — Integrated | UI is connected to Jarvis's shared command/runtime surfaces. |
| Q4 — Verified | Integration, safety, JavaScript validation, and regression contracts are verified. |
| Q5 — Scale | The next rung: expanded presentation capability while preserving or improving every Q4 contract. |

The current floor is Q4. A future Q5 UI must pass the same floor plus the new Q5-specific checks before it can become the new shipped floor.

## Runtime behavior

UI builds carry an explicit `quality_level`. New builds default to the current floor. Replacing an existing build with a lower quality level is rejected, and ordinary activation cannot switch from a higher quality build to a lower one.

The existing rollback path remains a safety recovery mechanism. It can restore a previously known presentation after a failed experiment, while the repository's verified quality floor itself never decreases.

## Performance guard

UI assets and the UI-build manager have explicit size budgets. The budgets are checked in CI so the UI can become richer without silently turning into an unbounded, heavier presentation layer. The packaged Windows smoke tests remain the final runtime gate for the real executable.

## Self-coding behavior

A self-coding pass now runs the repository quality-floor gate in addition to its configured tests. A coding change that passes its own unit tests but drops a protected integration contract cannot become a pending checkpoint.

Quality is allowed to scale upward; the guardrail is specifically designed to prevent "works, but worse than before" changes from becoming the new baseline.
