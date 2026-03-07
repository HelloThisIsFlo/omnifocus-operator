# Phase 12: SQLite Reader - Research

**Researched:** 2026-03-07
**Domain:** SQLite read path, row-to-model mapping, WAL freshness detection
**Confidence:** HIGH

## Summary

Phase 12 implements `HybridRepository` -- a `Repository` protocol implementation that reads OmniFocus data directly from the SQLite cache file. The SQLite schema is well-documented from prior research (`.research/deep-dives/direct-database-access/`), all field mappings are verified, and the freshness mechanism (WAL mtime polling) is proven. Zero new runtime dependencies -- stdlib `sqlite3` and `plistlib` handle everything.

The main implementation work is: (1) SQL queries across 5 tables + 1 join table, (2) row-to-Pydantic-model mapping with dual timestamp format parsing, (3) WAL-based freshness detection, (4) comprehensive test suite using in-memory SQLite fixtures.

**Primary recommendation:** Build HybridRepository as a single module (`repository/hybrid.py`) with internal helper functions for query building, timestamp parsing, and status mapping. Keep SQL as plain string constants -- no ORM, no query builder.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **HybridRepository** naming (not SQLiteRepository) -- lives at `repository/hybrid.py`
- DB path: default `~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel/OmniFocusDatabase.db`, override via `OMNIFOCUS_SQLITE_PATH` env var, constructor accepts `db_path: Path | None`
- Freshness built in Phase 12 (FRESH-01, FRESH-02 stay here)
- WAL `st_mtime_ns` polling: 50ms interval, 2s timeout
- WAL fallback: when WAL doesn't exist, use main `.db` file mtime
- Freshness is internal to HybridRepository -- consumers just call `get_all()`
- `TEMPORARY_simulate_write()` method on HybridRepository only (not on Repository protocol), with "Delete this method when real writes are implemented" comment
- Repository protocol stays clean: only `get_all() -> AllEntities`
- Test fixtures: in-memory SQLite via stdlib, shared `create_test_db()` helper
- UAT script in `uat/` folder (read-only, against real SQLite)

### Claude's Discretion
- Row-to-model mapping implementation (raw SQL queries, column name constants, etc.)
- Perspective `valueData` plist parsing approach (stdlib `plistlib`)
- Timestamp format detection and parsing (CF epoch vs ISO 8601)
- Module structure within `repository/` (helpers, query builders, etc.)
- Test factory API design and internal structure
- UAT script structure and validation assertions
- Error handling for corrupt/missing columns (fail-fast pattern established)

### Deferred Ideas (OUT OF SCOPE)
- Writes through Repository (future phase)
- Repository rename (future phase)
- Server wiring / env var routing (Phase 13)

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SQLITE-01 | Server reads OmniFocus data from SQLite cache (~46ms full snapshot) | Full schema mapping verified in 4-final-checks/FINDINGS.md; 5 tables + 1 join |
| SQLITE-02 | Read-only mode (`?mode=ro`) and fresh connection per read | stdlib `sqlite3.connect(f'file:{path}?mode=ro', uri=True)` verified working |
| SQLITE-03 | Maps rows to Pydantic models with two-axis status | Status columns (`overdue`, `dueSoon`, `blocked`, `dateCompleted`, `dateHidden`) all verified |
| SQLITE-04 | OmniFocus does not need to be running for reads | SQLite cache is a standalone file; verified in research PoC |
| FRESH-01 | WAL mtime polling after bridge write (50ms interval, 2s timeout) | WAL freshness mechanism proven in todo4_sqlite_freshness research |
| FRESH-02 | Fallback to main `.db` mtime when WAL doesn't exist | Simple `os.stat()` fallback; WAL absent = clean OmniFocus shutdown |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlite3` | stdlib (SQLite 3.51.0) | Database reads | Zero deps, read-only URI mode, WAL-aware |
| `plistlib` | stdlib | Parse Perspective `valueData` blobs | Binary plist parsing built-in |
| `os` | stdlib | WAL/DB file mtime via `os.stat()` | `st_mtime_ns` for nanosecond precision |
| `asyncio` | stdlib | `to_thread` for blocking I/O | Same pattern as `FileMtimeSource` |
| `pydantic` | existing dep | Model validation | Already used throughout codebase |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pathlib` | stdlib | Path construction for DB/WAL paths | Constructor parameter type |
| `datetime` | stdlib | Timestamp parsing (CF epoch conversion) | `datetime.fromtimestamp()` for CF epoch floats |
| `time` | stdlib | Polling sleep in freshness loop | `asyncio.sleep` in async context |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw SQL strings | aiosqlite | Adds dependency; `asyncio.to_thread` is sufficient for ~46ms reads |
| Raw SQL strings | SQLAlchemy | Massive overkill for read-only queries on a known schema |
| `plistlib` | Custom parser | No reason; `plistlib.loads()` handles binary plists perfectly |

**Installation:** No new dependencies required.

## Architecture Patterns

### Recommended Project Structure
```
repository/
    __init__.py          # Add HybridRepository export
    protocol.py          # Repository protocol (unchanged)
    bridge.py            # BridgeRepository (unchanged)
    in_memory.py         # InMemoryRepository (unchanged)
    hybrid.py            # NEW: HybridRepository implementation
```

Keep `hybrid.py` as a single module. Internal organization via private functions/constants at module level. If it grows past ~400 lines, extract helpers to `repository/_sqlite_queries.py` or similar -- but don't pre-split.

### Pattern 1: Fresh Connection Per Read
**What:** Open a new `sqlite3.connect()` for every `get_all()` call, close it when done.
**When to use:** Always -- prevents stale WAL reads.
**Example:**
```python
# Source: research/todo4_sqlite_freshness/FINDINGS.md
def _read_all(db_path: Path) -> dict:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row  # column access by name
    try:
        # ... execute queries ...
        return results
    finally:
        conn.close()
```

### Pattern 2: WAL Freshness Polling
**What:** After marking state as stale, poll WAL mtime until it changes, then read.
**When to use:** After `TEMPORARY_simulate_write()` is called (future: after real writes).
**Example:**
```python
# Source: research/RESULTS.md section 3
async def _wait_for_fresh_data(self) -> None:
    wal_path = self._db_path.parent / (self._db_path.name + "-wal")
    baseline = self._last_wal_mtime_ns
    deadline = time.monotonic() + 2.0  # 2s timeout
    while time.monotonic() < deadline:
        try:
            current = (await asyncio.to_thread(os.stat, wal_path)).st_mtime_ns
        except FileNotFoundError:
            # WAL doesn't exist -- fall back to main DB mtime
            current = (await asyncio.to_thread(os.stat, self._db_path)).st_mtime_ns
        if current != baseline:
            return  # Fresh data available
        await asyncio.sleep(0.05)  # 50ms poll
    # Timeout: proceed anyway (data may be slightly stale)
```

### Pattern 3: Dual Timestamp Parsing
**What:** SQLite columns store timestamps in two formats that must be auto-detected.
**When to use:** Every date field.
**Example:**
```python
from datetime import datetime, timezone

# Core Foundation epoch: Jan 1, 2001 00:00:00 UTC
_CF_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)

def _parse_timestamp(value: str | float | None) -> str | None:
    """Parse CF epoch float or ISO 8601 string to ISO 8601 with timezone."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # CF epoch float (seconds since 2001-01-01)
        dt = _CF_EPOCH + timedelta(seconds=value)
        return dt.isoformat()
    if isinstance(value, str):
        # ISO 8601 string -- may or may not have timezone
        if not value.endswith("Z") and "+" not in value:
            return value + "+00:00"  # Assume UTC for bare timestamps
        return value
    msg = f"Unexpected timestamp type: {type(value)}"
    raise ValueError(msg)
```

### Pattern 4: Two-Axis Status Mapping from SQLite Columns
**What:** Map independent SQLite boolean columns to Urgency + Availability enums.
**When to use:** Every Task and Project row.
**Example:**
```python
def _map_urgency(*, overdue: int, due_soon: int) -> str:
    if overdue:
        return "overdue"
    if due_soon:
        return "due_soon"
    return "none"

def _map_task_availability(
    *, blocked: int, date_completed: object, date_hidden: object
) -> str:
    if date_hidden is not None:
        return "dropped"
    if date_completed is not None:
        return "completed"
    if blocked:
        return "blocked"
    return "available"
```

### Anti-Patterns to Avoid
- **Reusing SQLite connections:** Opens door to stale WAL reads. Always fresh connection.
- **Caching query results:** The 46ms read time makes caching unnecessary. HybridRepository has no `_cached` field for SQLite reads (unlike BridgeRepository which caches because bridge calls are 1-3s).
- **ORM mapping:** Adding SQLAlchemy or similar for 5 read-only queries is pure overhead.
- **Async SQLite libraries:** `aiosqlite` wraps `sqlite3` in a thread anyway. `asyncio.to_thread` does the same thing with zero deps.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Binary plist parsing | Custom parser | `plistlib.loads(blob)` | Handles all Apple plist formats (binary, XML) |
| Timezone-aware datetime | Manual tz handling | Pydantic's `AwareDatetime` validation | Let Pydantic enforce timezone awareness on model construction |
| Status computation | Re-derive from dates/flags | Read pre-computed SQLite columns (`blocked`, `overdue`, `dueSoon`) | OmniFocus computed these; reimplementing risks divergence |
| Review interval parsing | Parse `@1w`/`~2m` format | Regex or string split | Simple enough, but don't invent a parser class |

**Key insight:** OmniFocus pre-computes status in the SQLite cache. The whole point of the SQLite path is to use those pre-computed values rather than reimplementing OmniFocus's blocking/urgency logic.

## Common Pitfalls

### Pitfall 1: Core Foundation Epoch vs Unix Epoch
**What goes wrong:** Treating CF epoch floats as Unix timestamps (off by ~31 years).
**Why it happens:** Both are "seconds since epoch" but CF epoch starts at 2001-01-01, Unix at 1970-01-01.
**How to avoid:** Detect format: if value is numeric, it's CF epoch. Add `978307200` seconds (CF-to-Unix offset) or use `datetime(2001,1,1) + timedelta(seconds=value)`.
**Warning signs:** Dates showing up in the 1990s when they should be 2020s.

### Pitfall 2: `dateHidden` Means "Dropped", Not "Hidden"
**What goes wrong:** Ignoring `dateHidden` or mapping it to a "hidden" concept.
**Why it happens:** Column name is misleading. In OmniFocus, "hidden" is the internal term for "dropped."
**How to avoid:** Map `dateHidden` -> `drop_date`, `effectiveDateHidden` -> `effective_drop_date`. Verified via OmniJS cross-check (4-final-checks/FINDINGS.md).
**Warning signs:** Tasks with `dropped` availability showing `None` for `drop_date`.

### Pitfall 3: Tag Table is Called "Context"
**What goes wrong:** Looking for a `Tag` table that doesn't exist.
**Why it happens:** OmniFocus originally called tags "contexts" and the SQLite schema retains the legacy name.
**How to avoid:** Query `Context` table for tags. Same for `TaskToTag` join table -- it exists as-is.
**Warning signs:** `sqlite3.OperationalError: no such table: Tag`

### Pitfall 4: Tag Status Uses `allowsNextAction` + `dateHidden`
**What goes wrong:** Looking for a `status` or `active` column on the Context table.
**Why it happens:** No such column exists. Tag status is derived from two columns.
**How to avoid:** `allowsNextAction=0` -> `blocked`, `dateHidden IS NOT NULL` -> `dropped`, else -> `available`.
**Warning signs:** All tags showing as `available` (ignoring blocked/dropped states).

### Pitfall 5: Project Data Split Across Two Tables
**What goes wrong:** Trying to get all project fields from the `Task` table alone.
**Why it happens:** Projects are stored as Tasks (with a `ProjectInfo` record linked by `persistentIdentifier`). Review dates, folder, next_task, and effective status live on `ProjectInfo`.
**How to avoid:** JOIN `Task` with `ProjectInfo` on `Task.persistentIdentifier = ProjectInfo.task` (or `ProjectInfo.pk`). The `ProjectInfo` table has its own `pk` column that references the task's `persistentIdentifier`.
**Warning signs:** Missing `lastReviewDate`, `nextReviewDate`, `folder` on projects.

### Pitfall 6: Perspective Name Is Inside a Plist Blob
**What goes wrong:** Looking for a `name` column on the Perspective table.
**Why it happens:** Perspective table has only 5 columns: `persistentIdentifier`, `creationOrdinal`, `dateAdded`, `dateModified`, `valueData`.
**How to avoid:** Parse `valueData` as binary plist via `plistlib.loads()`, extract `name` key.
**Warning signs:** Perspectives with no name, or attempting to read a column that doesn't exist.

### Pitfall 7: Stale Reads from Connection Reuse
**What goes wrong:** Data doesn't reflect recent OmniFocus changes.
**Why it happens:** SQLite WAL readers see a snapshot from when their transaction started. Reusing a connection can read stale data.
**How to avoid:** Fresh `sqlite3.connect()` per `get_all()` call. Close immediately after.
**Warning signs:** Data appears frozen even though OmniFocus has been modified.

## Code Examples

### Complete SQLite Table-to-Model Mapping

From verified research (4-final-checks/FINDINGS.md):

**Task table columns -> Task model fields:**
```
persistentIdentifier     -> id
name                     -> name
dateAdded                -> added          (CF epoch float)
dateModified             -> modified       (CF epoch float)
noteXMLData              -> note           (XML -> plaintext extraction needed)
flagged                  -> flagged        (0/1 integer)
effectiveFlagged         -> effective_flagged (0/1 integer)
dateDue                  -> due_date       (ISO 8601 or CF epoch)
dateToStart              -> defer_date     (ISO 8601 or CF epoch -- "start" = "defer")
effectiveDateDue         -> effective_due_date
effectiveDateToStart     -> effective_defer_date
dateCompleted            -> completion_date
effectiveDateCompleted   -> effective_completion_date
dateHidden               -> drop_date      (NOT "hidden" -- means "dropped")
effectiveDateHidden      -> effective_drop_date
datePlanned              -> planned_date
effectiveDatePlanned     -> effective_planned_date
estimatedMinutes         -> estimated_minutes
childrenCount            -> has_children   (> 0 = True)
inInbox                  -> in_inbox       (0/1 integer)
containingProjectInfo    -> project        (reference to ProjectInfo)
parent                   -> parent         (reference to parent Task)
overdue                  -> urgency mapping (0/1 integer)
dueSoon                  -> urgency mapping (0/1 integer)
blocked                  -> availability mapping (0/1 integer)
```
URL: constructed as `omnifocus:///task/{persistentIdentifier}`

**ProjectInfo table columns -> Project-specific fields:**
```
task                     -> (join key to Task.persistentIdentifier)
lastReviewDate           -> last_review_date
nextReviewDate           -> next_review_date
reviewRepetitionString   -> review_interval (parse "@1w"/"~2m" format)
nextTask                 -> next_task
folder                   -> folder
effectiveStatus          -> project availability (contains literal 'dropped', 'inactive')
```

**Context (Tag) table columns -> Tag fields:**
```
persistentIdentifier     -> id
name                     -> name
dateAdded                -> added
dateModified             -> modified
allowsNextAction         -> availability (0=blocked, 1=available/check dateHidden)
dateHidden               -> availability (non-NULL=dropped)
childrenAreMutuallyExclusive -> children_are_mutually_exclusive
parent                   -> parent
```
URL: `omnifocus:///tag/{persistentIdentifier}`

**Folder table columns -> Folder fields:**
```
persistentIdentifier     -> id
name                     -> name
dateAdded                -> added
dateModified             -> modified
dateHidden               -> availability (NULL=available, non-NULL=dropped)
parent                   -> parent
```
URL: `omnifocus:///folder/{persistentIdentifier}`

**Perspective table -> Perspective fields:**
```
persistentIdentifier     -> id (NULL for built-in)
valueData                -> name (parse binary plist, extract "name" key)
```
Built-in detection: `persistentIdentifier` is NULL or a human-readable string like `ProcessCompleted`.

**TaskToTag join table:**
```
task                     -> task persistentIdentifier
context                  -> tag persistentIdentifier
```

### RepetitionRule from SQLite Columns
```python
def _build_repetition_rule(row: sqlite3.Row) -> dict | None:
    rule_string = row["repetitionRuleString"]
    if not rule_string:
        return None
    schedule_type_raw = row["repetitionScheduleTypeString"]
    # Map SQLite values to enum values
    schedule_type_map = {
        "fixed": "regularly",
        "due-after-completion": "from_completion",
        "start-after-completion": "from_completion",
    }
    anchor_map = {
        "dateDue": "due_date",
        "dateToStart": "defer_date",
        # datePlanned also possible
    }
    return {
        "ruleString": rule_string,
        "scheduleType": schedule_type_map.get(schedule_type_raw, schedule_type_raw),
        "anchorDateKey": anchor_map.get(row["repetitionAnchorDateKey"], "due_date"),
        "catchUpAutomatically": bool(row["catchUpAutomatically"]),
    }
```

### ReviewInterval Parsing
```python
import re

def _parse_review_interval(raw: str | None) -> dict:
    """Parse '@1w' or '~2m' format into {steps, unit}."""
    if not raw:
        return {"steps": 7, "unit": "days"}  # OmniFocus default
    match = re.match(r"[~@](\d+)([dwmy])", raw)
    if not match:
        return {"steps": 7, "unit": "days"}
    count, unit_char = int(match.group(1)), match.group(2)
    unit_map = {"d": "days", "w": "weeks", "m": "months", "y": "years"}
    return {"steps": count, "unit": unit_map.get(unit_char, unit_char)}
```

### Note XML Extraction
```python
def _extract_note_text(xml_data: bytes | None) -> str:
    """Extract plain text from OmniFocus note XML.

    Notes are stored as XML: <text><p><run><lit>content</lit></run></p></text>
    Return empty string for NULL or empty notes.
    """
    if not xml_data:
        return ""
    # Simple approach: strip XML tags
    import re
    text = xml_data.decode("utf-8", errors="replace")
    # Remove XML tags, collapse whitespace
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()
```

### Project Availability from SQLite
```python
def _map_project_availability(
    *, effective_status: str | None, date_completed: object, date_hidden: object
) -> str:
    """Map ProjectInfo.effectiveStatus + Task dates to Availability."""
    if date_hidden is not None:
        return "dropped"
    if effective_status == "dropped":
        return "dropped"
    if date_completed is not None:
        return "completed"
    if effective_status == "inactive":
        return "blocked"  # "inactive" = on hold
    return "available"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bridge IPC for all reads (1-3s) | SQLite direct read (~46ms) | Phase 12 | 20-60x speedup, no OmniFocus process needed |
| Single-winner status enum | Two-axis (urgency + availability) | Phase 10 | Independent blocked + overdue tracking |
| Connection pooling | Fresh connection per read | Research finding | Prevents stale WAL reads |

**Deprecated/outdated:**
- `OmniFocusRepository` alias: removed in Phase 11, replaced by `BridgeRepository`
- `get_snapshot()`: renamed to `get_all()` in Phase 11
- `DatabaseSnapshot`: renamed to `AllEntities` in Phase 11

## Open Questions

1. **Note XML format edge cases**
   - What we know: Notes stored as XML in `noteXMLData` column. Simple cases have `<text><p><run><lit>...</lit></run></p></text>` structure.
   - What's unclear: Rich text notes with multiple paragraphs, attachments, or formatting. How deep does the XML nesting go?
   - Recommendation: Start with simple regex tag stripping. If edge cases surface in UAT, switch to `xml.etree.ElementTree` parsing. The bridge also returns plain text, so we have a reference.

2. **Project join key**
   - What we know: `ProjectInfo` has a `task` column referencing Task. Also has its own `pk`.
   - What's unclear: Exact join syntax -- is it `ProjectInfo.task = Task.persistentIdentifier` or `ProjectInfo.pk = Task.persistentIdentifier`?
   - Recommendation: Verify in the first implementation task. The research scripts used both; either works. Test fixture will confirm.

3. **Built-in perspective detection from SQLite**
   - What we know: Bridge uses `id === null` for built-in. In SQLite, built-in perspectives have human-readable IDs like `ProcessCompleted`.
   - What's unclear: Whether built-in perspectives have NULL `persistentIdentifier` in SQLite or always have these readable IDs.
   - Recommendation: Check in UAT. If they have non-NULL IDs, detect built-in via a known-ID set or by ID format (no UUID pattern).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run pytest tests/ -x --timeout=10` |
| Full suite command | `uv run pytest tests/ --timeout=30` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SQLITE-01 | Full snapshot loads from in-memory SQLite | unit | `uv run pytest tests/test_hybrid_repository.py::test_read_all_entities -x` | Wave 0 |
| SQLITE-02 | Connection uses `?mode=ro`, fresh per read | unit | `uv run pytest tests/test_hybrid_repository.py::test_read_only_connection -x` | Wave 0 |
| SQLITE-03 | Rows map to models with two-axis status | unit | `uv run pytest tests/test_hybrid_repository.py::test_status_mapping -x` | Wave 0 |
| SQLITE-04 | Reads succeed without OmniFocus running | integration | `uv run pytest tests/test_hybrid_repository.py::test_reads_without_omnifocus -x` | Wave 0 |
| FRESH-01 | WAL mtime change triggers fresh read | unit | `uv run pytest tests/test_hybrid_repository.py::test_freshness_wal_polling -x` | Wave 0 |
| FRESH-02 | Falls back to DB mtime when no WAL | unit | `uv run pytest tests/test_hybrid_repository.py::test_freshness_db_fallback -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_hybrid_repository.py -x --timeout=10`
- **Per wave merge:** `uv run pytest tests/ --timeout=30`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_hybrid_repository.py` -- covers SQLITE-01 through FRESH-02
- [ ] Test helper: `create_test_db()` function (in test file or conftest) -- builds in-memory SQLite with schema and seed rows
- [ ] UAT script: `uat/test_sqlite_reader.py` -- validates against real OmniFocus SQLite

## Sources

### Primary (HIGH confidence)
- `.research/deep-dives/direct-database-access/RESULTS.md` -- architecture decisions, WAL freshness, two-axis model
- `.research/deep-dives/direct-database-access/RESULTS_pydantic-model.md` -- complete field-level contract
- `.research/deep-dives/direct-database-access/4-final-checks/FINDINGS.md` -- column corrections, all 6 failures resolved
- `.research/deep-dives/direct-database-access/3-validation-todos/todo4_sqlite_freshness/FINDINGS.md` -- WAL polling mechanism
- `.research/deep-dives/direct-database-access/1-initial-discovery/FINDINGS.md` -- SQLite schema, table structure
- Existing codebase: `repository/protocol.py`, `repository/bridge.py`, `bridge/mtime.py`, all model files

### Secondary (MEDIUM confidence)
- SQLite WAL documentation: [sqlite.org/wal.html](https://www.sqlite.org/wal.html) -- WAL read visibility guarantees

### Tertiary (LOW confidence)
- Note XML format complexity -- only simple cases observed in research; edge cases need UAT validation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- stdlib only, all APIs verified on Python 3.12 / SQLite 3.51.0
- Architecture: HIGH -- follows established codebase patterns (Repository protocol, async wrapping, fresh-connection-per-read)
- Field mapping: HIGH -- every field verified against real SQLite schema with OmniJS cross-check
- Freshness mechanism: HIGH -- proven in research with real data, documented SQLite guarantee
- Pitfalls: HIGH -- all 6 failed fields resolved with corrected column names
- Note XML parsing: LOW -- simple cases only; may need refinement in UAT

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (stable -- OmniFocus schema unchanged since 2008)
