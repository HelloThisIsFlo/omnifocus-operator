# Direct Database Access — Results

> SQLite cache for reads, OmniJS bridge for writes, two-axis status model, graceful degradation.

- **Primary read path:** SQLite cache (~46ms full snapshot, OmniFocus doesn't need to be running)
- **Write path:** OmniJS bridge (unchanged — OmniFocus must be running)
- **Status model:** Two independent axes (Urgency + Availability) replace the single `status` enum
- **Read-after-write:** Poll WAL file mtime for freshness (~500ms delay)
- **Fallback:** Manual switch to OmniJS bridge via env var when SQLite is unavailable
- **Field coverage:** All model fields verified against SQLite schema ([Pydantic model](RESULTS_pydantic-model.md))

---

## 1. Architecture

- SQLite cache = primary read path (~46ms full snapshot, filtered queries <6ms, no caching layer needed)
- OmniJS bridge = write path only (unchanged)
- **Why SQLite over XML:** pre-computed status flags (`blocked`, `overdue`, `dueSoon`, `blockedByFutureStartDate`) as independent columns, computed by OmniFocus itself. XML would require reimplementing blocking logic.
- **Schema stability:** same SQL queries have worked OF1 (2008) through OF4 (2023). Every reported breakage was a path change, never a schema change.

**SQLite cache location:**
```
~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus/
  com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel/OmniFocusDatabase.db
```

---

## 2. Two-Axis Status Model

The OmniJS bridge returns a single-winner `taskStatus` enum where conditions compete — a task is Overdue OR Blocked, never both. This masks real state. Details in [`todo2_enum_priority/FINDINGS.md`](3-validation-todos/todo2_enum_priority/FINDINGS.md).

We replace the single enum with two independent axes:

**Urgency** (is this pressing?):
- `overdue` — past due date
- `due_soon` — approaching due date
- `none` — no time pressure

**Availability** (can this be worked on?):
- `available` — ready to work on
- `blocked` — structurally blocked (sequential ordering, project on hold, etc.)
- `completed` — has been completed
- `dropped` — has been dropped

SQLite provides both axes as independent columns. No reimplementation, no divergence risk.

> `next` (first available in sequential project) was considered but dropped — not present in SQLite or OmniJS, niche use case.

---

## 3. Read-After-Write: WAL Polling

~500ms delay between bridge write and SQLite readability. Freshness signal: WAL file's `st_mtime_ns`.

```
Before bridge write:
    wal_mtime_before = os.stat(WAL_PATH).st_mtime_ns

After bridge write:
    Poll every 50ms (up to 2s timeout):
        if os.stat(WAL_PATH).st_mtime_ns != wal_mtime_before:
            -> Open fresh connection and read. Data is guaranteed ready.
```

Why this works: in WAL mode, readers read directly from the WAL file. WAL write = data queryable. This is a documented SQLite design guarantee.

**WAL file location:** same directory as the `.db` file, with `-wal` suffix.

---

## 4. Fallback: OmniJS Bridge

When SQLite is not found (e.g., OmniFocus version changed the path), the server enters **error-serving mode**:

> "SQLite database not found at [path]. Either update the path, or set `OMNIFOCUS_BRIDGE=omnijs` to use the OmniJS bridge temporarily."

**Manual switch, not automatic** — must be visible. The idea: daily review breaks, set the env var, fix it later.

**Status quality in OmniJS mode — reduced but usable:**

- **Urgency:** fully preserved (Overdue always beats Blocked in the bridge enum)
- **Availability:** reduced to `available` · `completed` · `dropped` (no `blocked`):
  - `completed` = `completed` boolean field (ground truth)
  - `dropped` = `not effective_active` (covers self-dropped and inherited)
  - `available` = everything else (caveat: may actually be blocked)
- Good enough for daily use — urgency is the primary query axis, and completed/dropped are reliably derivable. Only loss: `blocked` vs `available` distinction.

---

## 5. Updated Pydantic Model

The two-axis status model drives significant changes to the Pydantic models. `TaskStatus`, `ProjectStatus`, `active`, `effective_active`, and `completed` (bool) are all replaced by `urgency: Urgency` + `availability: Availability` on `ActionableEntity`.

Full field listing, mapping tables, removed fields with rationales, and fallback mode behavior: [`RESULTS_pydantic-model.md`](RESULTS_pydantic-model.md)

---

## 6. Deep-Dive References

For investigation details, methodology, and raw data:

| Phase | What it covers | Link |
|-------|---------------|------|
| Initial Discovery | XML bundle format, SQLite schema, field coverage analysis, PoC parser, prior art | [`1-initial-discovery/FINDINGS.md`](1-initial-discovery/FINDINGS.md) |
| Walk Exploration | The conversation that led to "SQLite over XML", two-axis model, degraded mode design, error-serving MCP pattern | [`2-walk-exploration/direct-db-access-walk-findings.md`](2-walk-exploration/direct-db-access-walk-findings.md) |
| TODO 1: Cache Timing | Confirmed SQLite updates 2-59ms after bridge writes (two-phase commit) | [`3-validation-todos/todo1_cache_timing/FINDINGS.md`](3-validation-todos/todo1_cache_timing/FINDINGS.md) |
| TODO 2: Enum Priority | Confirmed Overdue always beats Blocked; degraded mode preserves urgency | [`3-validation-todos/todo2_enum_priority/FINDINGS.md`](3-validation-todos/todo2_enum_priority/FINDINGS.md) |
| TODO 3: SQLite Benchmark | Full snapshot 46ms, filtered <6ms — no caching layer needed | [`3-validation-todos/todo3_sqlite_benchmark/FINDINGS.md`](3-validation-todos/todo3_sqlite_benchmark/FINDINGS.md) |
| TODO 4: Freshness Detection | WAL `st_mtime_ns` is the best zero-cost freshness signal; ~500ms delay | [`3-validation-todos/todo4_sqlite_freshness/FINDINGS.md`](3-validation-todos/todo4_sqlite_freshness/FINDINGS.md) |
| Final Checks: Field Coverage | 51/52 fields from SQLite; verified column mappings for all 6 failures | [`4-final-checks/FINDINGS.md`](4-final-checks/FINDINGS.md) |
