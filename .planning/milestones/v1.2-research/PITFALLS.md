# Pitfalls Research

**Domain:** Adding write capabilities (task creation, editing, lifecycle) to an existing read-only OmniFocus MCP server
**Researched:** 2026-03-07
**Confidence:** HIGH (based on codebase analysis, BRIDGE-SPEC empirical data, and OmniJS constraints)

## Critical Pitfalls

### Pitfall 1: Snapshot Invalidation Race -- Write Completes Before OmniFocus Flushes to SQLite

**What goes wrong:**
Write goes through OmniJS bridge (modifies OmniFocus in-memory state), Python marks snapshot stale, next `get_all()` reads from SQLite -- but OmniFocus hasn't flushed to the SQLite cache yet. The "fresh" read returns pre-write data.

**Why it happens:**
Write path: Python -> bridge.js -> OmniFocus (in-memory) -> SQLite cache (async flush). The SQLite cache is a read-only mirror updated on OmniFocus's schedule. WAL mtime polling (50ms intervals, 2s timeout) was designed for external changes, not for changes the server triggered via bridge.

**How to avoid:**
- After a successful bridge write, use the bridge's return value (created/edited entity ID) as source of truth -- don't immediately re-read from SQLite to "confirm"
- For `add_tasks`, return the ID from bridge response directly
- `TEMPORARY_simulate_write()` on HybridRepository already has the right invalidation pattern -- replace with real call
- Add a UAT test that does write-then-read to measure actual flush latency

**Warning signs:**
- UAT tests doing `add_tasks` then `get_task` intermittently return stale data
- WAL mtime doesn't change within 2s timeout after a bridge write

**Phase to address:**
Phase 2 (add_tasks) -- first write, must validate invalidation flow end-to-end in UAT

---

### Pitfall 2: OmniJS Has No Transactions -- Partial Writes Are Permanent

**What goes wrong:**
Batch `edit_tasks` modifies items 1-2 successfully, throws on item 3 (invalid tag). Items 1-2 are already modified in OmniFocus -- no rollback. Bridge returns error, Python reports failure, but 2/5 items are silently changed.

**Why it happens:**
BRIDGE-SPEC Section 4: "OmniJS applies changes immediately. If a script throws partway through, already-applied changes persist." `document.undo()` undoes only the last discrete action, not a sequence.

**How to avoid:**
- **Validate everything before touching OmniFocus.** Service layer checks all IDs exist, tag names resolve, mutually-exclusive constraints pass. Bridge receives a fully-validated payload.
- **Start with single-item constraint.** v1.2 spec: "Start with single-item constraint (array of exactly one)." Eliminates partial failure entirely.
- **Never rely on `document.undo()` for programmatic rollback.**

**Warning signs:**
- Service layer passes unvalidated data to bridge
- Bridge.js processes items in a loop without per-item error handling
- Tests only cover the happy path

**Phase to address:**
Phase 2 (add_tasks) -- enforce single-item. Phase 3 (edit_tasks) -- same.

---

### Pitfall 3: `markIncomplete()` Is a Silent No-Op on Dropped Tasks

**What goes wrong:**
Agent reactivates a dropped task via `markIncomplete()`. No error thrown, but task remains dropped. Agent assumes success.

**Why it happens:**
BRIDGE-SPEC Section 4: "`markIncomplete()` on Dropped task: Silent no-op. No error, no state change. Dropping is permanent for standalone tasks."

**How to avoid:**
- Service layer must check task's current availability before lifecycle operations
- Bridge must verify post-operation state and error if unchanged
- Consider making "reactivate dropped task" an explicit unsupported operation with clear error
- Research spike: test whether `document.undo()` immediately after `drop()` can reverse it

**Warning signs:**
- Lifecycle tests that mock bridge responses without testing real OmniFocus behavior
- No UAT test for drop-then-reactivate flow

**Phase to address:**
Phase 4 (lifecycle changes) -- requires research spike before implementation

---

### Pitfall 4: `assignedContainer` Is Always Null -- Task Movement API Is Unverified

**What goes wrong:**
Developer uses `task.assignedContainer = project` to move tasks. Returns null on all 2,825 tasks -- it's a read-only property that never had a value.

**Why it happens:**
BRIDGE-SPEC Section 2.1 "Do NOT use" list: "`t.assignedContainer` -- always null on all tasks (2825/2825)." Actual task movement API is an open question in the v1.2 spec.

**How to avoid:**
- **Research spike required before implementing task movement.** Test in OmniJS:
  1. `moveTasks([task], project)` (document-level method)
  2. Direct `task.containingProject` assignment (may not be writable)
  3. Re-creating task in target project (nuclear option, loses history)
- Do NOT implement until empirically verified

**Warning signs:**
- Bridge.js using `assignedContainer` for writes
- Task movement implemented without UAT

**Phase to address:**
Phase 3 (edit_tasks movement) -- research spike at phase start

---

### Pitfall 5: Repeating Task Completion Creates New Instance with New ID

**What goes wrong:**
Agent completes a repeating task. OmniFocus marks current instance complete and spawns a successor with a new ID. Agent's reference to the original ID now points to the completed instance. Subsequent edits hit the wrong task.

**Why it happens:**
OmniFocus repeating tasks are individual tasks that spawn successors. `markComplete()` completes the instance; new instance gets a fresh `id.primaryKey`. v1.2 spec identifies this as an open question.

**How to avoid:**
- Check `task.repetitionRule` before completion -- if non-null, return supplementary data
- Bridge response for repeating task completion should include `{completed_id, successor_id}`
- `drop(false)` skips one occurrence; `drop(true)` drops all -- expose distinction clearly
- Test: "complete repeating task, look up old ID" must return completed task, not the new one

**Warning signs:**
- Bridge `edit_task` handler doesn't check repetition rules before lifecycle changes
- Tests use only non-repeating tasks
- No test for post-completion ID behavior

**Phase to address:**
Phase 4 (lifecycle) -- requires research spike

---

### Pitfall 6: `flattenedTasks` Scan for Get-by-ID Operations Freezes OmniFocus UI

**What goes wrong:**
`get_task(id)` is implemented by iterating `flattenedTasks` in bridge.js to find the matching ID. 2,800 tasks * 1ms/task = 2.8 seconds of frozen OmniFocus UI.

**Why it happens:**
BRIDGE-SPEC Section 1: "1ms per task per operation" -- every property access in OmniJS is expensive. The snapshot pattern works because it's a single bulk read. Per-entity lookups via iteration are prohibitively slow.

**How to avoid:**
- Use `Task.byIdentifier(id)` for direct lookup (documented in BRIDGE-SPEC Section 7 as available API)
- Similarly `Project.byIdentifier(id)`, `Tag.byIdentifier(id)` for other entity types
- Verify these APIs exist and work in UAT before relying on them
- For the bridge-based get-by-ID path, consider falling back to the cached snapshot dict lookup (already loaded in memory for BridgeRepository)

**Warning signs:**
- Bridge.js get_task handler using `.filter()` or `.find()` on `flattenedTasks`
- UAT showing multi-second response times for single entity lookups

**Phase to address:**
Phase 1 (get-by-ID tools) -- use `byIdentifier()` from day one

---

### Pitfall 7: Tag Name Ambiguity -- OmniFocus Allows Duplicate Tag Names

**What goes wrong:**
`add_tasks` with `tags: ["Meeting"]` when two tags named "Meeting" exist (under "Work" and "Personal"). Bridge picks first match silently.

**Why it happens:**
BRIDGE-SPEC Section 2.3: "Unique in observed data but OmniFocus allows duplicates." v1.2 spec uses tag names (not IDs) for agent ergonomics.

**How to avoid:**
- Service layer must check for duplicate tag names during validation
- If ambiguous, return error listing duplicates with IDs and parent paths
- Accept both tag names and IDs (detect by format -- IDs are UUIDs/alphanumeric strings)
- Consider qualified names like "Work/Meeting" for disambiguation

**Warning signs:**
- Tag lookup using `next(t for t in tags if t.name == name)` without duplicate check
- Tests using only unique tag names

**Phase to address:**
Phase 2 (add_tasks) -- tag validation is part of service-layer input validation

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Single-item arrays only (no batch) | Eliminates partial failure complexity | Must add batch later for agent productivity | v1.2 -- extend when pipeline proven |
| Return bridge response without re-reading full entity | Fast, avoids SQLite flush race | Returned object may lack computed fields (urgency, availability) | v1.2 -- agent can `get_task` for full state |
| No retry on bridge write timeout | Simpler error handling | Timed-out write may have succeeded | v1.2 -- retry is v1.5 scope |
| Lifecycle deferred to phase 4 | Avoids research spike blocking simple edits | Later phases depend on lifecycle understanding | Always acceptable -- spec already plans this |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| OmniJS writes | Using `task.parentTask` for re-parenting | `task.parent` -- `parentTask` does not exist in Omni Automation |
| OmniJS writes | Using `task.project` to set project | `task.containingProject` -- `task.project` returns null for child tasks |
| OmniJS dates | Passing ISO8601 strings to date fields | OmniJS needs `Date` objects: `new Date("2024-01-15T10:30:00Z")` |
| OmniJS tags | Assigning tag names to `task.tags` | `task.addTag(tagObject)` -- must look up `Tag` object first via `flattenedTags` or `Tag.byIdentifier()` |
| OmniJS notes | Setting `task.note = null` to clear | `task.note` is never null -- set to `""` instead |
| File IPC | Writing JSON without atomic rename | Use `.tmp` + `os.replace()` (already established in `_write_request`) |
| Repository protocol | Adding write methods without updating all implementations | `InMemoryRepository`, `BridgeRepository`, `HybridRepository` all need write methods |
| SQLite path | Expecting writes through SQLite | SQLite is read-only (`?mode=ro`). All writes go through OmniJS bridge |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Iterating `flattenedTags` in OmniJS per task in a batch | Multi-second freeze per batch item | Resolve all tag names to Tag objects once upfront | Any batch > 5 items with tags |
| Full snapshot reload after every write | 46ms (SQLite) or multi-second (bridge) per write | Invalidate only; let next read trigger reload | Rapid sequential writes |
| `flattenedTasks` scan for lookups | 2.8s freeze for one task lookup | `Task.byIdentifier(id)` for O(1) lookup | Every get-by-ID call |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent success when write did nothing (e.g., `markIncomplete` on dropped) | Agent reports success, task unchanged | Bridge verifies post-state; errors if unchanged |
| Returning only `{success, id}` without task state | Agent needs second call to see what was created | Return `{success, id, name}` minimum (spec requirement) |
| Confusing error when project + parent_task_id both set | Agent doesn't know which to remove | Message: "project and parent_task_id are mutually exclusive" |
| Tag errors showing IDs instead of names | Agent sees "Unknown tag: jK4x..." | Error messages must include tag names |
| `null` vs `omit` confusion in edit payloads | Agent clears fields by accident | Tool description must clearly explain patch semantics: omit=no change, null=clear, value=set |

## "Looks Done But Isn't" Checklist

- [ ] **add_tasks:** Task with no project AND no parent goes to Inbox (`inInbox: true`)
- [ ] **add_tasks:** `planned_date` is v4.7+ -- older OmniFocus silently ignores it
- [ ] **edit_tasks tags:** `tags` with `add_tags` is a validation error; `add_tags` + `remove_tags` is allowed
- [ ] **edit_tasks null:** Every nullable field can actually be cleared via OmniJS (some may not accept null)
- [ ] **edit_tasks movement:** Task disappears from old project's task list, not just re-pointed
- [ ] **Snapshot invalidation:** Next `list_all` after write returns updated data
- [ ] **Bridge errors:** OmniJS errors surface as clear MCP messages, not raw stack traces
- [ ] **InMemoryRepository:** Write methods added -- tests fail silently if missing
- [ ] **Repository protocol:** Extended with write methods; all 3 implementations satisfy it
- [ ] **Bridge response:** `add_task` returns the new task's `id.primaryKey`, not some other identifier

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Partial batch write (1-2 applied, 3-5 failed) | LOW | Report per-item results. Agent retries failed items. |
| Write succeeded but snapshot stale | LOW | Force invalidation + re-read. WAL mtime catches up. |
| Task moved to wrong project | LOW | Edit again with correct project ID. No data lost. |
| Repeating task completed, lost successor ID | MEDIUM | Query by name/project to find new instance. Return successor ID to prevent. |
| Dropped task cannot be reactivated | HIGH | `document.undo()` only works if nothing else happened since. Otherwise recreate task. History lost. |
| Tag assigned incorrectly (name ambiguity) | LOW | Remove wrong tag, add correct one. Implement disambiguation. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Snapshot invalidation race | Phase 2 (add_tasks) | UAT: create task, immediately get_task -- data is fresh |
| No transactions / partial failure | Phase 2 (add_tasks) | Enforce single-item. Test invalid input caught before bridge |
| `markIncomplete()` no-op on dropped | Phase 4 (lifecycle) | Research spike + UAT: drop, attempt reactivate, verify error |
| `assignedContainer` always null | Phase 3 (edit_tasks movement) | Research spike + UAT: move task between projects |
| Repeating task ID changes | Phase 4 (lifecycle) | Research spike. Bridge returns successor ID |
| `flattenedTasks` scan for lookup | Phase 1 (get-by-ID) | Use `Task.byIdentifier(id)`. UAT: verify < 200ms |
| Tag name ambiguity | Phase 2 (add_tasks) | Test: two tags with same name, verify disambiguation error |
| OmniJS date objects | Phase 2 (add_tasks) | Bridge.js must `new Date()` from ISO strings. UAT: verify dates round-trip |
| Repository protocol extension | Phase 1 (get-by-ID) | All 3 implementations satisfy updated protocol |

## Sources

- BRIDGE-SPEC.md -- empirical spec from 27 audit scripts against live OmniFocus v4.8.8
- MILESTONE-v1.2.md -- spec with open questions and phasing hints
- Codebase: bridge.js (IPC protocol), real.py (trigger mechanism), hybrid.py (SQLite reader + WAL freshness), bridge.py (BridgeRepository caching), service.py, protocol.py
- OmniJS performance constraint: 1ms/task/operation (BRIDGE-SPEC Section 1)

---
*Pitfalls research for: v1.2 Writes & Lookups*
*Researched: 2026-03-07*
