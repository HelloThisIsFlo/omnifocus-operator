# Bridge Benchmark

Isolates where the ~3s `handleSnapshot()` bottleneck lives in bridge.js.

## Usage

```bash
uv run python .research/benchmark/run.py [--runs 5] [--warmup 2]
```

Each variant triggers OmniFocus via URL scheme — you'll need to accept the
script prompts manually. This is a human-run exploration tool (same safety
rules as UAT/SAFE-02).

## Variants

| # | What it maps | Isolates |
|---|-------------|----------|
| 01 | Empty arrays | Pure IPC overhead |
| 02 | Just primary keys | Iteration cost |
| 03 | id, name, note | String property access |
| 04 | + all date fields | Date.toISOString cost |
| 05 | + enum-resolved fields | Enum comparison cost |
| 06 | Full tasks, empty others | Task vs other entity breakdown |
| 07 | Full handleSnapshot | Baseline (current bridge.js) |
