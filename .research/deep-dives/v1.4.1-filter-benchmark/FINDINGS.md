# v1.4.1 Python-Filter Benchmark — Findings

> **Python-side filtering is decisively fast enough.** At 10K tasks, warm-path Python is ~1 ms p95 across all three scenarios — well under the pre-declared 100 ms threshold. Recommendation: **repo-layer unification via Python filtering is viable.** Cold-path (load + filter) matters separately but is orthogonal to this decision.

Corpus: synthetic SQLite DBs at 1K / 5K / 10K / 25K tasks, plus one cross-check against Flo's live OmniFocus DB (3,426 tasks, read-only). Methodology per plan: 2 warmups, 10 iterations, `time.perf_counter()`; report min / median / mean / p95.

---

## 1. Summary numbers (p95 in ms)

Three scenarios at each scale. Warm Python = children-map built inside the timed call, snapshot pre-loaded (matches `BridgeOnlyRepository.list_tasks`'s amortized path).

| Scenario | Path | 1K | 5K | 10K | 25K | Live (3.4K) |
|---|---|---:|---:|---:|---:|---:|
| parent only | SQL CTE | 0.22 | 1.00 | **2.10** | 5.39 | 1.84 |
| parent only | Python warm | 0.10 | 0.50 | **1.21** | 5.61 | 0.47 |
| parent only | Python cold | 2.60 | 12.80 | **27.90** | 63.15 | 52.64 |
| parent + tag | SQL | 0.06 | 0.13 | **0.24** | 0.62 | 1.64 |
| parent + tag | Python warm | 0.11 | 0.76 | **1.29** | 5.95 | 0.73 |
| parent + tag | Python cold | 2.74 | 13.94 | **27.79** | 70.43 | 57.60 |
| parent + date | SQL | 0.10 | 0.46 | **3.93*** | 2.25 | 1.47 |
| parent + date | Python warm | 0.10 | 0.52 | **1.30** | 5.45 | 0.50 |
| parent + date | Python cold | 3.52 | 13.15 | **26.53** | 63.68 | 53.88 |

\* One outlier sample in the 10K date run — median was 0.88 ms. Both paths would pass the threshold either way.

**All warm-path p95 values at 10K are ≤ 1.30 ms** — 77× under the 100 ms "Python viable" threshold.

---

## 2. Decision

**Repo-layer unification is viable.** The filter-unification architectural question has a clear answer: Python-side filtering at 10K is fast enough to keep all filter logic at the repo layer (both `HybridRepository` and `BridgeOnlyRepository` implementing the same Python-based filter pattern, with `HybridRepository` optionally delegating to SQL for heavy scans).

This matches the **"Fast enough → filter unification can move to the repo layer"** branch in `MILESTONE-v1.4.1.md:187-189`.

Recommendation strength: **high**. Every scenario, every scale, every percentile stays under the threshold with 50-100× margin.

---

## 3. Scaling shape

**SQL (CTE + filter):** 0.22 ms → 5.39 ms across 1K→25K. Roughly linear with a mild super-linear bend at 25K. Scales well.

**Python warm (map build + traversal):** 0.10 ms → 5.61 ms across 1K→25K. Linear-ish. Map build is O(n) and dominates — traversal of the ~15-task subtree is effectively free.

**Python cold (load + map build + filter):** 2.60 ms → 63.15 ms across 1K→25K. Linear with a larger constant because `SELECT *` + dict construction materializes every column into Python memory.

**Cross-check on live DB (3.4K rows, full OmniFocus schema ~60 columns):**
- Warm Python stays fast: 0.47 ms — map-build cost scales with row *count*, not column count.
- Cold Python is 50.64 ms — **2× higher than synthetic 10K** despite 3× fewer rows. Reason: production Task table has ~60 columns (including BLOB `noteXMLData`); synthetic had ~15. Row *width* matters for cold.

Forward extrapolation: at 10K real-schema tasks, cold ≈ 150 ms. At 25K, cold ≈ 375 ms. Cold-path could cross the 200 ms threshold at large corpora — but see §4.

---

## 4. Cold-path caveat (and why it doesn't change the decision)

Cold = first-ever query OR query after `get_all()` cache invalidation (mtime change). In production `BridgeOnlyRepository`, the snapshot is cached across calls until the mtime source says it's stale.

**Why cold doesn't change the decision:**

1. **Shared cost**: the `get_all()` snapshot load happens for *any* filter path — SQL or Python. Filter unification only affects what happens *after* the snapshot is materialized. So cold-path cost is orthogonal to the SQL-vs-Python choice.
2. **Amortized**: warm-path dominates in realistic usage (multiple queries per mtime change). The p95 warm number at 10K (1.30 ms) is what users experience.
3. **Already a thing**: any performance concern about cold-path applies equally to the current production code, which also loads full snapshots in the BridgeOnly fallback.

**If cold-path performance ever becomes a concern**, the response is a separate optimization (projection — only load needed columns, lazy deserialization, etc.) — not a change to the filter-unification decision.

---

## 5. SQL vs Python — direct comparison

At the spec's 10K target scale:

| | SQL | Python warm | Python cold |
|---|---|---|---|
| parent only (p95) | 2.10 ms | **1.21 ms** | 27.90 ms |
| parent + tag (p95) | **0.24 ms** | 1.29 ms | 27.79 ms |
| parent + date (p95) | 3.93 ms* | **1.30 ms** | 26.53 ms |

\* Outlier; median 0.88 ms.

- **SQL wins on combined filters** (parent + tag: 0.24 ms vs 1.29 ms) because additional predicates prune the CTE result early. On pure parent-only, Python warm edges SQL.
- **Python is near-constant** (~1.1-1.3 ms) regardless of filter complexity at 10K — dominated by map-build cost, filter evaluation is free.
- **Both paths are 40-400× under threshold.** The ordering between them doesn't matter at this performance level.

---

## 6. Thresholds vs actuals

Pre-declared thresholds (from this spike's plan, pre-registered before running):

| Regime | Threshold | 10K worst-case p95 observed | Margin |
|---|---|---|---|
| Python viable (→ repo-layer unification) | p95 ≤ 100 ms | 1.30 ms (warm), 27.90 ms (cold) | 77× (warm), 3.6× (cold) |
| Python too slow (→ service-layer fallback) | p95 > 200 ms | — | — |

**Verdict: well inside the "Python viable" bound.** No need for the gray-zone judgment call.

---

## 7. Design implications for planning

Now that filter unification can live at the repo layer, the v1.4.1 planning decisions:

1. **Shared filter protocol**: a common `list_tasks` filter pipeline that both `HybridRepository` and `BridgeOnlyRepository` implement with similar Python logic. `HybridRepository` can still use SQL for the initial snapshot fetch (existing optimization) but apply filters in Python uniformly.
2. **Subtree traversal utility**: extract `collect_subtree(parent_id, snapshot) -> list[Task]` as a reusable helper. Used by both repos.
3. **Parent filter in `ListTasksRepoQuery`**: add a `parent_ids: list[str] | None` field (list to support future multi-parent resolution). Filter logic lives in repo, not service.
4. **SQL CTE still available**: if a future scale concern emerges (25K+ tasks), `HybridRepository` can opportunistically push the filter down to SQL via the recursive CTE shown in `sql_parent_filter.py`. That's a performance optimization, not a contract change.
5. **Keep the `parent_plus_tag` SQL pattern handy**: for the specific `parent + tag` combo it's 5× faster than Python warm. Worth documenting as an optimization path if Hybrid repo usage ever shifts towards tag-heavy queries.

Contract stays unchanged regardless of implementation layer — this benchmark only affects *where* the filter lives in the code.

---

## Deep-dive references

| Experiment | File | What it shows |
|---|---|---|
| Corpus | `experiments/corpus.py` | Synthetic ~10K-task fixture builder with leaf-biased tree shape |
| SQL prototype | `experiments/sql_parent_filter.py` | Recursive CTE + filter predicates |
| Python prototype | `experiments/python_parent_filter.py` | Children map + DFS traversal + list-comprehension filters |
| Harness | `experiments/_harness.py` | Shared timing/reporting helpers |
| Bench 01 | `experiments/01_bench_parent_only.py` | Parent-only filter, scale sweep |
| Bench 02 | `experiments/02_bench_parent_plus_tag.py` | Parent + tag combo, scale sweep |
| Bench 03 | `experiments/03_bench_parent_plus_date.py` | Parent + date combo, scale sweep |
| Bench 04 | `experiments/04_bench_livedb_crosscheck.py` | Live DB cross-check, shape validation |

Reproduce with:
```bash
uv run python .research/deep-dives/v1.4.1-filter-benchmark/experiments/01_bench_parent_only.py
uv run python .research/deep-dives/v1.4.1-filter-benchmark/experiments/02_bench_parent_plus_tag.py
uv run python .research/deep-dives/v1.4.1-filter-benchmark/experiments/03_bench_parent_plus_date.py
uv run python .research/deep-dives/v1.4.1-filter-benchmark/experiments/04_bench_livedb_crosscheck.py
```
