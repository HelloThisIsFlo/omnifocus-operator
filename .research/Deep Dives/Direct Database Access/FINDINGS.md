# Direct Database Access — Findings

> Can we read the OmniFocus database directly, bypassing the Omni Automation bridge?

**Date:** 2026-03-06
**Status:** Research complete, PoC validated

## Summary

**Yes.** The OmniFocus database can be read directly via two independent paths:

1. **`.ofocus` XML bundle** — the source of truth, stable format since OF2 (2014)
2. **SQLite cache** — an internal cache with pre-computed fields, faster but less stable

Both approaches bypass OmniFocus entirely for reads. Writes still require the
bridge (OmniFocus must process mutations for consistency, sync, and undo).

## Three Read Paths Compared

| Approach | Full Read | Cached | Field Coverage | Stability | OmniFocus Required? |
|----------|-----------|--------|----------------|-----------|---------------------|
| **SQLite cache** | ~11ms | N/A | 100% (all effective/computed fields) | Internal detail, moves across versions | No |
| **XML .ofocus** | ~120ms | 0.003ms (mtime check) | ~95% (must compute effective fields) | Stable since OF2 (2014) | No |
| **Bridge IPC** | ~1-3s | N/A | 100% | Official API | Yes, must be running |

Benchmarks on real database: 2826 tasks, 79 folders, 65 tags, 50 perspectives.

---

## 1. The `.ofocus` XML Bundle

### Location

```
~/Library/Containers/com.omnigroup.OmniFocus4/Data/Library/
  Application Support/OmniFocus/OmniFocus.ofocus/
```

Same path we already use for mtime-based cache invalidation (`DEFAULT_OFOCUS_PATH`).

### Structure

The `.ofocus` bundle is a directory (macOS package) containing:

```
OmniFocus.ofocus/
  00000000000000=djJA1ZB2YFr+dYNDTg2Sqi7.zip   ← base snapshot (full state)
  20260303004827=dYNDTg2Sqi7+iFoNBcT-wyu.zip    ← delta transaction
  20260303172654=iFoNBcT-wyu+gHgzT7BV-KG.zip    ← delta transaction
  ...more deltas...
  data/
    data-{sha256}.zip                             ← attachments (images, etc.)
  *.capability                                    ← format feature declarations
```

Each zip contains a single `contents.xml`. Filenames form a hash chain:
`YYYYMMDDHHMMSS=prevHash+thisHash.zip`. This means we can detect which
transactions are new by comparing filenames.

### XML Format

Namespace: `http://www.omnigroup.com/namespace/OmniFocus/v2`

| XML Element | Count | Maps To |
|-------------|-------|---------|
| `<task>` | 2820 | Tasks AND Projects (projects have a `<project>` child element) |
| `<task-to-tag>` | 4581 | Many-to-many task-tag links |
| `<folder>` | 79 | Folders |
| `<context>` | 65 | Tags (legacy XML name for what the UI calls "tags") |
| `<alarm>` | 55 | Notifications |
| `<perspective>` | 50 | Perspectives (stored as embedded plist) |
| `<setting>` | 35 | App settings (DueSoonInterval, DefaultStartTime, etc.) |
| `<attachment>` | 9 | File attachments (content in `data/` subdir) |

### Delta Operations

Subsequent transaction zips contain elements with `op` attributes:

| Operation | Meaning | Count in test DB |
|-----------|---------|-----------------|
| (none) | Insert new element | 473 |
| `op="update"` | Partial update (only changed fields) | 20 |
| `op="delete"` | Remove element | 467 |
| `op="reference"` | Context snapshot for other elements | 15 |

To reconstruct current state: parse base snapshot, then apply all deltas in order.

### Sample Task XML

```xml
<task id="aM1mzRcLBeV">
  <project/>           <!-- empty = not a project -->
  <inbox>false</inbox>
  <task idref="a03VIkt7v_4"/>  <!-- parent task reference -->
  <added order="23">2023-04-17T16:53:42.836Z</added>
  <name>Gather ideas for things to do on Mari's Birthday</name>
  <note><text><p><run><lit>Some note text</lit></run></p></text></note>
  <rank>1073741821</rank>
  <hidden/>
  <context idref="mz8OJ5umz47"/>  <!-- primary tag (legacy name) -->
  <start>2026-03-12T08:00:00.000</start>  <!-- defer date -->
  <due/>
  <completed/>
  <estimated-minutes>1</estimated-minutes>
  <order>parallel</order>
  <flagged>false</flagged>
  <completed-by-children>false</completed-by-children>
  <repetition-rule>FREQ=WEEKLY;INTERVAL=3;BYDAY=TH</repetition-rule>
  <repetition-method>start-after-completion</repetition-method>
  <modified>2026-02-16T17:54:02.456Z</modified>
</task>
```

### Sample Project XML

Projects are tasks with a non-empty `<project>` child:

```xml
<task id="eT0g7xNOI2_">
  <project>
    <folder idref="dhKt78l_09m"/>
    <singleton>false</singleton>
    <last-review>2025-12-02T16:07:12.120Z</last-review>
    <next-review>2026-03-10T00:00:00.000Z</next-review>
    <review-interval>~2w</review-interval>
    <status>active</status>
  </project>
  <inbox>false</inbox>
  <task/>  <!-- empty = no parent (top-level) -->
  <name>Store These Resources Somewhere</name>
  ...
</task>
```

### Key Relationships

- **Parent-child**: `<task idref="parentId"/>` inside a task element
- **Task-to-tag**: Separate `<task-to-tag>` elements with `<task idref>` + `<context idref>`
- **Project-to-folder**: `<folder idref>` inside the `<project>` child element
- **Folder hierarchy**: `<folder idref="parentId"/>` inside a folder element
- **Tag hierarchy**: `<context idref="parentId"/>` inside a context element

### Settings Available in XML

The `<setting>` elements contain useful configuration:

| Setting ID | Value | Notes |
|------------|-------|-------|
| `DueSoonInterval` | 86400 (seconds) | Used to compute DueSoon status |
| `DueSoonGranularity` | 1 | |
| `DefaultStartTime` | "08:00:00" | Default defer time |
| `DefaultDueTime` | "19:00:00" | Default due time |
| `OFMCompleteWhenLastItemComplete` | true | Auto-complete projects |
| `OFMAutomaticallyHideCompletedItems` | false | |
| `_ForecastBlessedTagIdentifier` | (tag id) | Forecast tag |

### Lock File

The `.ofocus-lock` file is informational only (plist with host, pid, process info).
It does NOT use OS-level file locking (`flock`). The transaction-based design is
inherently safe for concurrent reads — each zip is written atomically.

---

## 2. The SQLite Cache

### Location

```
~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus/
  com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel/OmniFocusDatabase.db
```

Note: The group container ID (`34YW5XSRB7`) is Omni Group's team ID and is
stable, but the path has changed with every major OmniFocus version.

### Schema

| Table | Rows | Notes |
|-------|------|-------|
| Task | 2826 | Includes project-tasks |
| TaskToTag | 4581 | Join table |
| Context | 65 | Tags |
| Folder | 79 | |
| ProjectInfo | 368 | Separate table for project metadata |
| Perspective | 50 | |
| Setting | 35 | |
| Alarm | 55 | |
| Attachment | 9 | |

### Key Advantage: Pre-computed Fields

The SQLite cache includes columns that OmniFocus computes at runtime:

```
blocked                              INTEGER
blockedByFutureStartDate             INTEGER
dueSoon                              INTEGER
overdue                              INTEGER
effectiveFlagged                     INTEGER
effectiveDateDue                     timestamp
effectiveDateToStart                 timestamp
effectiveDateCompleted               timestamp
effectiveDatePlanned                 timestamp
effectiveContainingProjectInfoActive INTEGER
childrenCount                        INTEGER
childrenCountAvailable               INTEGER
childrenCountCompleted               INTEGER
```

These are **independent boolean columns**, not a single-winner enum. This means
`blocked=1 AND overdue=1` is representable — solving the "overdue masks blocked"
problem that exists in the bridge's `taskStatus` enum.

### Stability Assessment (researched)

**Risk level: Low-frequency, high-predictability.**

The SQLite cache path has changed with every major version (~every 5-6 years):

| Version | Year | Location |
|---------|------|----------|
| OF1 | 2008 | `~/Library/Caches/.../OmniFocusDatabase2` |
| OF2 | 2014 | `~/Library/Containers/com.omnigroup.OmniFocus2/Data/Library/Caches/.../OmniFocusDatabase2` |
| OF3 | 2018 | `~/Library/Containers/com.omnigroup.OmniFocus3/.../OmniFocus Caches/` |
| OF3.5 | ~2020 | `~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus/...OmniFocus3/...` (surprise mid-cycle!) |
| OF4 | 2023 | `~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus/...OmniFocus4/...` |

**Key insight: Path changes killed tools, not schema changes.** An Omni Group
staff member confirmed during OF2 launch that "the sqlite cache moved to a new
location, but its format shouldn't have changed, and the queries still work once
you have the correct path." Core tables (Task, ProjectInfo, Folder, Context)
have survived across multiple major versions.

Omni Group has **never endorsed direct SQLite access** — the official path is
Omni Automation (JavaScript). The SQLite file is a cache that can be rebuilt
from the canonical `.ofocus` XML. There is no guarantee it will continue to exist.

Sources: [OF2 schema impact thread](https://discourse.omnigroup.com/t/of2-change-database-schema-impact-rob-trew-apple-scripts-updated-scripts-in-thread/4106),
[SQLite path change thread](https://discourse.omnigroup.com/t/sqlite-omnifocus-no-longer-updating-omnifocusdatabase-file/52652)

---

## 3. Field Coverage: XML vs Bridge

### Fields we CAN get from XML (~95%)

**Direct from XML:**
- id, name, note, added, modified
- flagged, completed (bool from date presence), completionDate
- dueDate, deferDate (XML: `<start>`), plannedDate, dropDate
- estimatedMinutes, sequential (XML: `<order>`), completedByChildren
- inInbox, repetitionRule (iCal RRULE string), repetitionMethod
- parent (XML: `<task idref>`), project folder, tags (via `<task-to-tag>`)

**Computable from XML (walking parent chains):**
- effectiveFlagged — inherits down from parent
- effectiveDueDate — inherits down from parent
- effectiveDeferDate — inherits down from parent
- effectiveCompletionDate — inherits down from parent
- effectiveDropDate, effectivePlannedDate — same pattern
- hasChildren — check if any task references this as parent
- url — `omnifocus:///task/{id}`
- project (containing project) — walk parent chain up to find project
- active / effectiveActive — project status + folder status chain

**Status computation (approximate):**
- Completed — has completion date
- Blocked — parent is sequential and this isn't first available child, OR project on-hold
- Overdue — due date in the past
- DueSoon — due within `DueSoonInterval` setting (86400s by default)
- Available — not blocked, not completed, not overdue/due-soon
- Next — first available in sequential project (approximation)

### Fields we CANNOT get from XML

**None.** All 73 bridge fields are either direct, constructible, or computable:

- **49 fields**: Direct from XML (no computation)
- **4 fields**: Constructible (url = `omnifocus:///{type}/{id}`)
- **20 fields**: Computable from XML data (effective fields, status, hasChildren, etc.)
- **0 fields**: Strictly impossible

Even `shouldUseFloatingTimeZone` — initially thought impossible — is inferrable
from the date format (dates without Z suffix = floating, with Z = UTC). In
practice it appears to be `true` for all tasks.

See `field_coverage_analysis.md` for the complete field-by-field breakdown.

### Key Insight: Independent Status Flags > Single Enum (Solves Overdue-Masks-Blocked)

The bridge returns a single `taskStatus` enum where conditions compete:
a task is Overdue OR Blocked, never both. **In your database, 173 tasks are
both blocked AND overdue** — the single enum masks this, misleading AI agents
into thinking these are actionable.

Both direct-access approaches solve this:

- **SQLite**: Already has independent columns `blocked`, `overdue`, `dueSoon`,
  `blockedByFutureStartDate` (pre-computed by OmniFocus itself)
- **XML**: We compute independent booleans ourselves (requires reimplementing
  blocking logic, but gives us full control)

Proposed data model with independent flags:
```python
class Task:
    blocked: bool                       # can't be worked on
    blocked_by_future_start_date: bool  # deferred to future
    overdue: bool                       # past due date
    due_soon: bool                      # approaching due date
    status: TaskStatus                  # OmniFocus's single-winner enum (for compat)
```

Query: `WHERE overdue AND NOT blocked` gives **265 actionable overdue tasks**
(vs 438 the single enum misleadingly reports)

---

## 4. Prior Art

| Project | Language | Status | Notes |
|---------|----------|--------|-------|
| [rubyfocus](https://github.com/jyruzicka/rubyfocus) | Ruby | Unmaintained | Most complete .ofocus parser, handles delta merging |
| [focus](https://github.com/kumpelblase2/focus) | Kotlin/JVM | Active | CLI + library, perspective-like filtering |
| [ofocus-format](https://github.com/tomzx/ofocus-format) | Docs | Reference | Reverse-engineered format spec (v1 + v2 branch) |
| [pyomni](https://github.com/taxpon/pyomni) | Python | Older | Basic task manipulation |
| [1klb.com blog](https://1klb.com/posts/2025/04/27/omnifocus_taskwarrior/) | Ruby | 2025 | Recent OF→Taskwarrior migration using XML parsing |

No production-quality Python library exists for OF4. Our PoC is arguably the
most complete Python implementation.

The `.ofocus` v2 format has been stable since OmniFocus 2 (2014). OF4 additions
(planned dates, mutually exclusive tags, enhanced repeats) use NEW XML elements —
existing elements are unchanged. The `.capability` files declare which features
are active in a given database.

---

## 5. Proposed Hybrid Architecture

```
READS:  .ofocus XML parse  →  Python data model  →  MCP tools
        (~120ms, no OmniFocus needed)

WRITES: MCP tool  →  bridge.js  →  OmniFocus URL scheme  →  .ofocus updated
        (~1-3s, OmniFocus must be running)

CACHE:  Watch .ofocus dir mtime_ns  →  re-parse only when new zips appear
        (0.003ms for cache hit, ~120ms for re-parse)
```

### Why XML over SQLite?

- XML is the **source of truth** — the sync format, not a cache
- Format has been stable for 12+ years
- SQLite cache path changes with every major version
- XML gives us all the data we need (effective fields are computable)
- XML parsing is fast enough (~120ms) and cacheable to 0.003ms

### Why keep the bridge for writes?

- OmniFocus must validate and process mutations
- Undo support requires OmniFocus involvement
- Sync to other devices requires OmniFocus
- Writing directly to the XML could corrupt the database

---

## 6. PoC Artifacts

All PoC code is in `/tmp/omnifocus-db-copy/` (not checked in — uses real data):

| File | Purpose |
|------|---------|
| `parse_ofocus.py` | Complete parser (300 lines): data classes, delta merging, bridge-format JSON output |
| `query_ofocus.py` | Interactive query tool: `inbox`, `due 7`, `overdue`, `search`, `project`, `tag` |
| `benchmark_parse.py` | Performance measurement (10 iterations) |
| `compare_with_bridge.py` | Field-by-field accuracy comparison with bridge output |
| `compute_effective_fields.py` | Analysis of which computed fields are reconstructable |
| `incremental_parse.py` | Caching demo with mtime-based invalidation |

### Running the PoC

```bash
# Summary + JSON output
python3 /tmp/omnifocus-db-copy/parse_ofocus.py

# Interactive queries
python3 /tmp/omnifocus-db-copy/query_ofocus.py

# Performance benchmark
python3 /tmp/omnifocus-db-copy/benchmark_parse.py

# Compare with bridge output
python3 /tmp/omnifocus-db-copy/compare_with_bridge.py
```

### Validation Results

Compared direct-parse output against bridge sample (`snapshot-sample.json`):
- **Tags**: All common entities match on key fields
- **Folders**: All common entities match on key fields
- **Tasks**: All fields match except date format trivia (`.000` vs `Z` suffix)
- **Projects**: Same — only date format normalization differences

---

## Open Questions

1. **Should we use XML or SQLite for reads?** (Recommendation: XML for stability)
2. **Should we replace the bridge entirely for reads, or keep it as fallback?**
3. **How do we handle the write path?** (Keep bridge IPC, or explore Omni Automation directly?)
4. **Do we need to support reading while OmniFocus is mid-write?** (Transaction design makes this safe)
5. **Impact on SAFE-01/SAFE-02?** (Direct parse is read-only — no risk to live data)
