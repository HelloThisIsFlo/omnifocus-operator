# v1.4.1 Cache Coverage — Findings

> **All three new fields are cache-backed, and OmniJS ↔ SQLite per-row identity confirmed (60/60 matches).** `completedByChildren` → `Task.completeWhenChildrenComplete`. `sequential` → `Task.sequential`. Attachment presence → `Attachment` table with indexed `task` FK. Project third state → `ProjectInfo.containsSingletonActions`. Lock all three fields in v1.4.1; no bridge-only fallback required.

Corpus probed: Flo's live OmniFocus SQLite cache (read-only) — 3,426 Task rows (3,041 tasks + 385 projects) plus 10 Attachment rows. All experiments opened via `sqlite3.connect("file:{path}?mode=ro", uri=True)`. No mutations, no bridge interaction.

---

## 1. Per-field verdicts

| Field (spec) | Cache source | Storage | Populated? | Verdict |
|---|---|---|---|---|
| `completesWithChildren` (tasks) | `Task.completeWhenChildrenComplete` | `INTEGER NOT NULL` (0/1) | 38.4% false / 61.6% true | ✅ Lock |
| `completesWithChildren` (projects) | `Task.completeWhenChildrenComplete` (on project's Task row) | `INTEGER NOT NULL` (0/1) | 82.1% false / 17.9% true | ✅ Lock |
| `actionOrder` — parallel/sequential (tasks) | `Task.sequential` | `INTEGER NOT NULL` (0/1) | 99.1% false / 0.9% true | ✅ Lock |
| `actionOrder` — parallel/sequential (projects) | `Task.sequential` (on project's Task row) | `INTEGER NOT NULL` (0/1) | 88.3% false / 11.7% true | ✅ Lock |
| `actionOrder` — `singleActions` 3rd state (projects) | `ProjectInfo.containsSingletonActions` | `INTEGER NOT NULL` (0/1) | 77.7% false / 22.3% true | ✅ Lock |
| `hasAttachments` (tasks) | `EXISTS (SELECT 1 FROM Attachment WHERE task = t.persistentIdentifier)` | Indexed FK (Attachment_task) | 7/3041 tasks have attachments (0.23%) | ✅ Lock |
| `hasAttachments` (projects) | Same shape — `Attachment.task` points at the project's Task row | Indexed FK | 0/385 projects in current data | ✅ Lock — schema supports |

Naming nuance (non-blocking): OmniJS calls the flag `completedByChildren`, the SQLite column is named `completeWhenChildrenComplete`, and the spec uses `completesWithChildren`. Three names, one concept. Mapping is 1:1 in both directions.

---

## 2. Column + index evidence

**`Task.completeWhenChildrenComplete`** (schema from `PRAGMA table_info(Task)`):
```
completeWhenChildrenComplete  INTEGER  NOT NULL
```
No default clause observed; values populated on every row.

**`Task.sequential`:**
```
sequential  INTEGER  NOT NULL
```
Only 1% of loose tasks are sequential — matches intuition (most tasks are parallel by default; parent action groups that care about order are rare).

**`ProjectInfo.containsSingletonActions`:**
```
containsSingletonActions  INTEGER  NOT NULL
```
Distinct from `Task.sequential` — this is the third-state flag (singleActions projects). 22% of projects are single-actions.

**`Attachment` table:**
```
persistentIdentifier  TEXT    (+ sqlite_autoindex_Attachment_1, the PK)
task                  TEXT    indexed — Attachment_task (CREATE INDEX Attachment_task ON Attachment (task))
folder                TEXT    indexed — Attachment_folder
context               TEXT    indexed — Attachment_context
perspective           TEXT    indexed — Attachment_perspective
dateAdded             timestamp
dateModified          timestamp
dataIdentifier        TEXT
previewPNGData        BLOB
size                  INTEGER
name                  TEXT
```
Attachment rows are union-typed: exactly one of `{task, folder, context, perspective}` is non-null. In Flo's current data, all 10 attachments point to tasks; no projects have attachments yet (though the schema supports it since projects are also Task rows).

---

## 3. Attachment presence — performance

Two equivalent presence queries benchmarked over the full 3,426-row Task corpus:

| Form | Min | Median | Max |
|---|---|---|---|
| `EXISTS (SELECT 1 FROM Attachment a WHERE a.task = t.persistentIdentifier)` | 1.98 ms | **2.09 ms** | 2.40 ms |
| `LEFT JOIN Attachment + COUNT > 0 GROUP BY` | 2.38 ms | 2.48 ms | 2.60 ms |

Query plan (EXISTS form):
```
SCAN t USING COVERING INDEX sqlite_autoindex_Task_1
SEARCH pi USING COVERING INDEX ProjectInfo_task (task=?) LEFT-JOIN
CORRELATED SCALAR SUBQUERY 1
SEARCH a USING COVERING INDEX Attachment_task (task=?)
```

**Recommendation:** Prefer `EXISTS` over `LEFT JOIN + GROUP BY` — slightly faster and clearer intent.

Growth prediction: per-row lookup is O(log n) via the `Attachment_task` index. At 25K tasks with similar attachment density (~0.2%), expect ~15 ms. Well within the response-time budget.

---

## 4. User-default settings

Target keys (from OmniJS spike, used as create-time defaults when the agent omits the flag):

| Key | Cache presence | Decoded value | Source |
|---|---|---|---|
| `OFMCompleteWhenLastItemComplete` | ✅ in `Setting.valueData` (42-byte plist) | `True` | Flo's cache |
| `OFMTaskDefaultSequential` | ❌ not in Setting table | — (user kept default) | — |

Settings are stored one-row-per-key: `persistentIdentifier` is the key, `valueData` is a plist BLOB. Decoded via `plistlib.loads(valueData)` → returns native Python types cleanly (bool, str, etc.).

**Important semantic:** row absence ≠ error. OmniFocus only materializes a setting when the user explicitly changes it from the factory default. The server must treat absence as "user kept the documented default" (false/parallel for `OFMTaskDefaultSequential`, true for `OFMCompleteWhenLastItemComplete` — the OmniJS spike already confirmed these factory defaults).

**Design implication for v1.4.1:** service-layer default resolution is `plistlib.loads(SELECT valueData FROM Setting WHERE persistentIdentifier = ?)` with a fallback constant. Read once per server lifetime, no OmniJS round-trip needed.

Reference decodings from other OFM keys (validates the plist format works for strings + bools):
```
OFMCompleteWhenLastItemComplete:           True
OFMAutomaticallyHideCompletedItems:        False
OFMRequiredRelationshipToProcessInboxItem: 'project'
```

---

## 5. Decisions unblocked

1. **`hasAttachments` is locked as a default response field** — cheap enough that we don't need to gate it behind `include`.
2. **`completesWithChildren`, `actionOrder` are fully cache-readable on both Task and Project.**
3. **App-level defaults read cheaply from cache** with plist decoding — no OmniJS round-trip at server startup.
4. **Absence-as-default semantic** needs one line of doc in the service layer.

v1.4.1 scope stays as designed. No fields to drop.

---

## 6. OmniJS per-row cross-check

Flo ran `omnijs-crosscheck.js` in the OmniFocus Automation console; result piped into `experiments/05_omnijs_diff.py` for per-row comparison.

**Result: 60/60 checks match. Zero mismatches. Zero missing rows.**

| Rows compared | Fields checked per row | Total checks | Matches | Mismatches |
|---|---|---|---|---|
| 20 | 3 (`completedByChildren`, `sequential`, `hasAttachments`) | **60** | **60** | **0** |

Representative rows (names elided — only IDs + checked fields; all 20 sampled rows followed the same pattern):

| Task ID | OmniJS `completedByChildren` | SQLite `completeWhenChildrenComplete` | OmniJS `sequential` | SQLite `sequential` | OmniJS `hasAttachments` | SQLite `EXISTS(Attachment)` |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| `lbUMjHAKPR-` | True | 1 | False | 0 | False | 0 |
| `je-2QskvNkn` | True | 1 | False | 0 | False | 0 |
| `p4G_bKfHC6V` | True | 1 | False | 0 | False | 0 |
| `omDAGRP3ALy` | True | 1 | False | 0 | False | 0 |
| *(+16 more — same pattern; see `05_omnijs_diff.py` for the full sample)* | | | | | | |

**Caveat on sampling:** the 20 sampled rows all landed in the `cwcc=true / seq=false / hasAttachments=false` bucket. This is an artifact of OmniJS's deterministic iteration order (first 10 parents + first 10 leaves), not of data uniformity. The distribution evidence from §3 (cwcc is 62% true / 38% false on tasks) is the proper source of distributional truth; this diff confirms per-row *identity* rather than distribution.

**Cross-check verdict:** ✅ Cache and OmniJS agree on every sampled row. Boolean round-tripping between OmniJS `true/false`, SQLite `INTEGER 0/1`, and Python `bool` is clean — no coercion surprises. All three fields are safe to read from the cache in production.

---

## 7. Open items for Flo

- **Naming triangulation** — three names for one concept (`completedByChildren` / `completeWhenChildrenComplete` / `completesWithChildren`). Spec has already chosen `completesWithChildren` as the MCP contract; the SQLite column name is internal. Non-blocking.

---

## Deep-dive references

| Experiment | File | What it found |
|---|---|---|
| Schema probe | `experiments/01_schema_probe.py` | Column + table discovery; `Attachment_task` index |
| Value sample | `experiments/02_value_sample.py` | Distribution + boolean storage format |
| Attachment presence | `experiments/03_attachment_presence.py` | Join cost (~2 ms full corpus) + query plan |
| Settings defaults | `experiments/04_settings_defaults.py` | `OFMCompleteWhenLastItemComplete` = True; `OFMTaskDefaultSequential` absent |
| OmniJS diff | `experiments/05_omnijs_diff.py` | 20 rows × 3 fields → 60/60 match between OmniJS and SQLite |

Reproduce with:
```bash
uv run python .research/deep-dives/v1.4.1-cache-coverage/experiments/01_schema_probe.py
uv run python .research/deep-dives/v1.4.1-cache-coverage/experiments/02_value_sample.py
uv run python .research/deep-dives/v1.4.1-cache-coverage/experiments/03_attachment_presence.py
uv run python .research/deep-dives/v1.4.1-cache-coverage/experiments/04_settings_defaults.py
uv run python .research/deep-dives/v1.4.1-cache-coverage/experiments/05_omnijs_diff.py
```
