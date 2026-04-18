# v1.4.1 Cache Coverage Spike

**Question:** Does the OmniFocus SQLite cache expose `completedByChildren`, `sequential`, and attachment-presence for both Task and ProjectInfo rows, or do any of these require per-row OmniJS bridge fallback?

**Blocker this resolves:** `MILESTONE-v1.4.1.md:172–181` — bridge-only fallback is a 30–60× read-path regression and kills the field. Per-field outcome:

- ✅ **Cache-backed** — column exists, populated, distribution sane → lock in v1.4.1.
- ⚠️ **Cache-present but empty / stale** → flag for cross-check.
- ❌ **Not cached** → scope out of v1.4.1.

## Autonomous scope

All experiments read the live OmniFocus SQLite cache in **read-only mode** via `sqlite3.connect("file:{path}?mode=ro", uri=True)`. Nothing else is touched — no OmniJS, no bridge, no writes. This is the same pattern production `HybridRepository` uses (`src/omnifocus_operator/repository/hybrid/hybrid.py:1`).

## How to run

From the repo root:

```bash
uv run python .research/deep-dives/v1.4.1-cache-coverage/experiments/01_schema_probe.py
uv run python .research/deep-dives/v1.4.1-cache-coverage/experiments/02_value_sample.py
uv run python .research/deep-dives/v1.4.1-cache-coverage/experiments/03_attachment_presence.py
uv run python .research/deep-dives/v1.4.1-cache-coverage/experiments/04_settings_defaults.py
```

Each script is self-contained: path-validates, opens read-only, prints findings to stdout.

## Experiments

| # | Script | Question |
|---|--------|----------|
| 01 | `01_schema_probe.py` | Do candidate columns exist on `Task` and `ProjectInfo`? (`PRAGMA table_info`) |
| 02 | `02_value_sample.py` | Are candidate columns populated? Distribution, null rate, boolean storage format. |
| 03 | `03_attachment_presence.py` | Where are attachments stored? Is cheap presence-test possible from SQLite? |
| 04 | `04_settings_defaults.py` | Are `OFMCompleteWhenLastItemComplete` / `OFMTaskDefaultSequential` in the cache, or OmniJS-only? |

## OmniJS cross-check (optional, Flo-run)

After running the SQLite experiments, `omnijs-crosscheck.js` dumps OmniJS-reported values for 20 sample task IDs. Flo pastes the output back; diff goes in FINDINGS. Cross-check confirms per-row *identity* between cache and OmniJS — a stronger guarantee than schema-level sanity alone.

## Findings

See [`FINDINGS.md`](./FINDINGS.md).
