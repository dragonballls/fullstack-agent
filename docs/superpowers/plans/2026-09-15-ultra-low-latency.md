# Ultra-Low-Latency OmniRoute Plan

Goal: minimize interactive latency while preserving model quality, collaboration, cloud-only routing, capability policy, confirmation, and regression safety.

- Keep deterministic operations off the model path whenever the runtime already expresses them.
- Prefer warmed healthy low-latency targets with stable ordering for unseen targets.
- Use bounded concurrent provider attempts only where racing improves time-to-first-success without changing the public API.
- Keep specialist fan-out bounded and preserve result ordering.
- Add deterministic mock benchmarks for single-target, warm-target, fallback, and parallel workloads.
- Do not claim performance gains without measured evidence.
