# v1.4.1 Python-Filter Benchmark

**Question:** Over a ~10K-task corpus, is Python-side filtering for the new `parent` subtree filter fast enough to unify filter logic at the **repo layer** (forfeits SQL optimization for a cleaner abstraction), or must we fall back to **service-layer** unification with each repo keeping its SQL implementation?

**Blocker this resolves:** `MILESTONE-v1.4.1.md:183–190` — architectural question only. Contract is unchanged either way.

## Pre-declared interpretation thresholds

Stated before running to avoid post-hoc rationalization:

- **Python viable (→ repo-layer unification)**: p95 parent-only at 10K ≤ **100ms**, and parent+combo ≤ **200ms**.
- **Python too slow (→ service-layer fallback)**: p95 > 200ms at 10K on any combo, OR growth curve worse than linear-ish.
- **Gray zone**: between those bounds — Flo's call.

Anchored to the 46 ms SQL baseline from the project README: ~2–4× tolerable for an architectural win; 10×+ kills the idea.

## Autonomous scope

- Synthetic corpus: in-memory SQLite only, no persistent state.
- Live cross-check: live SQLite cache read-only via `?mode=ro`.
- No OmniJS, no bridge, no mutation.

## How to run

From the repo root:

```bash
uv run python .research/deep-dives/v1.4.1-filter-benchmark/experiments/01_bench_parent_only.py
uv run python .research/deep-dives/v1.4.1-filter-benchmark/experiments/02_bench_parent_plus_tag.py
uv run python .research/deep-dives/v1.4.1-filter-benchmark/experiments/03_bench_parent_plus_date.py
uv run python .research/deep-dives/v1.4.1-filter-benchmark/experiments/04_bench_livedb_crosscheck.py
```

Each benchmark imports the shared `corpus.py` fixture builder and both prototype filters. Output: min / median / mean / p95 across 10 iterations (2 warmup), per scale (1K / 5K / 10K / 25K).

## Experiments

| # | Script | Scenario |
|---|--------|----------|
| `corpus.py` | fixture | Synthetic SQLite DB matching OmniFocus cache schema — parametrized corpus size. |
| `sql_parent_filter.py` | prototype | Recursive CTE for descendant collection + downstream filter. Mirrors how `build_list_tasks_sql` would grow. |
| `python_parent_filter.py` | prototype | Load snapshot, build parent→children map, Python-recursive descendant collect + list-comprehension filters. Mirrors `BridgeOnlyRepository.list_tasks`. |
| 01 | `01_bench_parent_only.py` | Pure subtree filter, no other predicates. |
| 02 | `02_bench_parent_plus_tag.py` | Parent + tag (realistic combo). |
| 03 | `03_bench_parent_plus_date.py` | Parent + date-bound (realistic combo). |
| 04 | `04_bench_livedb_crosscheck.py` | Scenarios 01–03 against live SQLite cache (read-only) — reality-check synthetic shape. |

## Findings

See [`FINDINGS.md`](./FINDINGS.md).
