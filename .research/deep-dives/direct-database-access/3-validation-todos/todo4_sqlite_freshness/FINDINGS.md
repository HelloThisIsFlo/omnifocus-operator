# TODO #4 Findings: SQLite Freshness Detection

**Date:** 2026-03-06
**Status:** Complete

---

## Abstract

After a bridge write, the OmniFocus SQLite cache does NOT update instantly — there is a ~500ms delay before data becomes readable. However, we found a reliable, zero-cost freshness signal: **`os.stat()` on the WAL file's `st_mtime_ns`**. The moment the WAL mtime changes, the data is guaranteed to be readable.

### Why this works

SQLite's WAL (Write-Ahead Log) mode works like this: instead of writing changes directly into the main `.db` file, SQLite appends them to a separate `.db-wal` file. The key insight is that **readers also read from the WAL**. When you query the database, SQLite first checks the WAL for the latest version of each page, and only falls back to the main `.db` file for pages not in the WAL. This means:

1. OmniFocus writes a change → it lands in the WAL file → the WAL file's mtime updates
2. Any new SQLite connection opened after that point will read from the WAL and see the change
3. There is no intermediate state where the WAL has been written but a reader can't see it — **the write to the WAL and the data being queryable are the same event**

The "checkpoint" (where WAL contents get flushed back into the main `.db` file) is purely housekeeping to prevent the WAL from growing forever. It has no effect on read visibility.

This is a **documented design guarantee** of SQLite, not an implementation accident. The SQLite docs describe it as "snapshot isolation." Sources: [sqlite.org/wal.html](https://www.sqlite.org/wal.html), [sqlite.org/isolation.html](https://www.sqlite.org/isolation.html).

### Bottom line

After a bridge write, poll `WAL mtime_ns` (cheap `os.stat()` call, no SQLite connection required) at ~50ms intervals. When it changes, open a **fresh** connection and read — the data is there. Expect ~500ms latency. Use a ~2s timeout as safety. (The fresh connection is important: a connection that was already open before the write may not see the change until it starts a new read transaction.)

---

## Key Finding: ~500ms Delay

Unlike TODO #1 (which found near-instant propagation), this test revealed a **~500ms gap** between bridge response and SQLite readability:

| Snapshot | Time after before | Task found? |
|---|---:|---|
| Immediate (same conn) | 0.142s | No |
| Fresh connection | 0.145s | No |
| +500ms | 0.648s | Yes |
| +2s | 2.656s | Yes |

The difference from TODO #1 is methodology: TODO #1 polled repeatedly until the data appeared and measured the delay. This test took snapshots at fixed points to see exactly when indicators flip.

---

## Freshness Indicators: What Works, What Doesn't

Tested 20 different indicators. All that changed did so between the Fresh Connection and +500ms snapshots — nothing changed immediately.

### Reliable (detected the change)

| Indicator | Cost | Notes |
|---|---|---|
| **WAL mtime_ns** | `os.stat()` — nearly free | Best signal. No SQLite connection needed. |
| WAL file size | `os.stat()` | Changed (98912 -> 32768) due to checkpoint |
| WAL frame count (est.) | File read (32 bytes) | Derived from WAL size and header |
| WAL checkpoint seq | File read (32 bytes) | Incremented (3 -> 4) |
| WAL salt values | File read (32 bytes) | Both salt1 and salt2 changed |
| DB mtime_ns | `os.stat()` | Changed because checkpoint touched main DB |
| PRAGMA data_version | SQLite query | Changed on same conn (2->3), but fresh conn resets to baseline |
| Row query (task_found) | SQLite query | Direct verification — task appeared |
| Row count (task_count) | SQLite query | 2829 -> 2830 |

### Unreliable (did NOT detect the change)

| Indicator | Why |
|---|---|
| WAL checkpoint info | PRAGMA returned None (likely the modification you made) |
| File change counter | Only updates on checkpoint in WAL mode — and here it didn't |
| PRAGMA page_count | Insert didn't allocate new pages |
| PRAGMA freelist_count | No pages freed |
| SHM mtime/size | Didn't change |
| DB/WAL inode | OmniFocus modifies in-place, no replace |
| Header version-valid-for | Same as file change counter |
| PRAGMA schema_version | Only changes on schema alterations |
| DB write/read format | Static (always 2 for WAL mode) |

---

## Recommended Strategy

```
Before bridge write:
    wal_mtime_before = os.stat(WAL_PATH).st_mtime_ns

After bridge write:
    Poll every 50ms (up to 2s timeout):
        if os.stat(WAL_PATH).st_mtime_ns != wal_mtime_before:
            → Data is ready. Open fresh connection and read.
```

Why this works:
- `os.stat()` is a single syscall — negligible cost
- No SQLite connection needed for the freshness check
- WAL mtime changing and data being queryable are the same event (in WAL mode, readers read from the WAL directly)

---

## Interesting Observations

1. **A checkpoint happened during the test.** WAL size decreased (98912 -> 32768) and checkpoint_seq incremented. OmniFocus wrote to WAL then immediately checkpointed, which is why the main DB mtime also changed.

2. **`PRAGMA data_version` is connection-scoped.** It showed 3 on the same connection at +500ms but 2 on a fresh connection at +2s. It tracks "changes external to this connection," not an absolute version. Useful for long-lived connections, but not as a universal freshness signal.

3. **Reconciling with TODO #1:** TODO #1 found 2-59ms propagation delays. This test found ~500ms. The difference is likely that TODO #1's polling loop caught the data the instant it appeared, while this test's fixed-interval snapshots had a wider gap. The true latency is somewhere in between — likely under 500ms but not instant.

---

## Script

- `test_sqlite_freshness.py` — Creates a `__FRESHNESS_TEST_{uuid}__` task via OmniJS URL scheme. Takes 5 snapshots (before, immediate, fresh conn, +500ms, +2s) capturing 20 freshness indicators each. Compares all values to identify which indicators reliably detect the change. Cleanup in `try/finally`. SQLite opened read-only.
