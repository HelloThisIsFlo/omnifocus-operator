---
status: resolved
phase: 57-parent-filter-filter-unification
source: [57-01-SUMMARY.md, 57-02-SUMMARY.md, 57-03-SUMMARY.md]
started: 2026-04-23T12:00:00Z
updated: 2026-04-24T01:45:00Z
gaps_resolved_by: [57-04, 57-05]
---

## Current Test

[testing complete]

## Tests

### 1. Verbatim-text lock drift (em-dash → double-hyphen)
expected: Discuss whether the post-phase ruff cleanup (18e25d5c) that replaced the em-dash with "--" should stand, be reverted, or update the specs to match. Specs still reference U+2014; code does not.
result: pass
resolution: Option (a) — intentional on the code side. Updated two spec files to match (`--`):
  - .research/updated-spec/MILESTONE-v1.4.1.md:180
  - .planning/phases/57-parent-filter-filter-unification/57-CONTEXT.md:168
  Edits uncommitted; awaiting user's commit decision.

### 2. Design decision: scope expansion lives at service layer (D-01/D-03)
expected: `expand_scope` in src/omnifocus_operator/service/subtree.py:28 is a pure, snapshot-based helper. Repos (hybrid query_builder and bridge_only) only see a flat `task_id_scope: list[str]` and apply trivial set-membership. Walk through the architecture: why is parent-child subtree expansion a service concern, not a repo concern? Does this keep the repo layer properly ignorant of OmniFocus hierarchy semantics?
result: pass
notes: |
  Walked through the architecture; separation confirmed. Two concerns surfaced and were resolved inline:

  Q1 (ordering): Does service-layer scope expansion change query result ordering? NO. The repo applies a `WHERE t.persistentIdentifier IN (?, ...)` set-membership clause — no ORDER BY. Outline ordering comes from a separate CTE elsewhere in `build_list_tasks_sql`. The `sorted(self._project_scope)` at service.py only gives deterministic SQL placeholder order (cache keys / bind-param reproducibility), not task output order.

  Q2 (naming): `expand_scope` reads action-first but hides what it returns, and I initially claimed the name mismatched the project-branch behavior (flat vs tree). Flo correctly corrected that — `task.project` is the containing project at any nesting depth (TASK_PROJECT_DESC), so the project branch *does* return the whole subtree, just via a denormalized flat lookup instead of a recursive walk. Renamed inline to `get_tasks_subtree(ref_id, snapshot)`.

  Rename scope:
    - Code (3): service/subtree.py, service/service.py, repository/hybrid/query_builder.py
    - Tests (5): test_service_subtree.py (+ `TestExpandScope` → `TestGetTasksSubtree`), test_list_pipelines.py, test_cross_path_equivalence.py, test_hybrid_repository.py, test_query_builder.py
    - Live docs (2): .planning/ROADMAP.md, .planning/REQUIREMENTS.md
    - Deliberately NOT touched (phase-57 frozen historical artifacts): 57-CONTEXT.md, 57-VERIFICATION.md, 57-{01,02}-SUMMARY.md, 57-{01,02}-PLAN.md, 57-RESEARCH.md, 57-PATTERNS.md, 57-DISCUSSION-LOG.md

  Post-rename gates:
    - `grep expand_scope src/ tests/` → 0 matches
    - `uv run pytest -x -q` → 2503 passed (97.58% coverage, unchanged)
    - `uv run ruff check src/omnifocus_operator/service/subtree.py` → All checks passed

### 3. Design decision: `task_id_scope` semantic shift (PK type change)
expected: Old `ListTasksRepoQuery.project_ids` held project PKs. New `task_id_scope` at contracts/use_cases/list/tasks.py:130 holds TASK PKs — same type, same default, but meaning shifted. Plan 01 split rename (Task 2a commit 84e4fb7b) from semantic rewrite (Task 2b commit 468b0add) for a clean git-bisect boundary. Walk through the decision — does the name "task_id_scope" convey the shift clearly? Was the 2a/2b bisect split worth it?
result: pass
notes: |
  Mental model confirmed: responsibility shifted from "repo expands project → tasks via SQL join" to "service pre-expands via get_tasks_subtree, repo does flat PK lookup." Same primitive now serves both `project` and `parent` filters at the repo layer — parent filter reuse comes for free. `task_id_scope` name conveys the shift adequately.

### 4. Design decision: 3-arg `resolve_inbox` behavioral delta
expected: `Resolver.resolve_inbox` at src/omnifocus_operator/service/resolve.py:217 now takes 3 args. Old 2-arg form returned early on `$inbox` consumption; new form flows through a unified post-consumption contradiction gate. Observable delta: `project="$inbox", parent="SomeTask"` now correctly raises `CONTRADICTORY_INBOX_PROJECT` (it was unrepresentable in the 2-arg form). Locked-error regression tests in tests/test_service_resolve.py (`test_resolve_inbox_3arg_existing_*`). Is the cross-side contradiction behavior correct? Is consolidating `$inbox` logic into one resolver the right call?
result: pass
notes: Unified post-consumption gate is the right shape. Cross-side `$inbox` + real-ref contradictions now raise symmetrically (new cases were unrepresentable in 2-arg form). Regression tests lock error-message constants via re.escape on imports so renames fail loudly at import time.

### 5. Design decision: warning predicates — D-13 exclusions
expected: `DomainLogic.check_filtered_subtree` at src/omnifocus_operator/service/domain.py:545 excludes `availability` from the "other filter" predicate (availability has a non-empty default — including it would destroy signal). `check_parent_project_combined` at line 575 is presence-based — fires even when both filters resolve to the same thing (so the warning fires on redundancy, not just intersection emptiness). Walk through both predicates — do the exclusions and the presence-vs-emptiness choice match how agents will actually use the filter surface?
result: pass
notes: |
  Predicate semantics (D-13 exclusions + presence-based WARN-03) match how agents use the filter surface.

  Hardening applied inline: renamed the imprecise "dimensional" terminology and added a CI-enforced classification drift test so a future non-pruning Patch field (e.g. `sort_by`) can't slip into the warning predicate silently.

  Renames in src/omnifocus_operator/service/domain.py:
    - `_SCOPE_WARN_DIMENSIONAL_FIELDS` → `_SUBTREE_PRUNING_FIELDS`
    - Added `_NON_SUBTREE_PRUNING_FIELDS = frozenset({"project", "parent"})`
    - `check_filtered_subtree` docstring + code ref updated

  New tests in tests/test_service_domain.py::TestSubtreePruningFieldsDrift:
    - `test_every_patch_field_is_classified` — every member of `_PATCH_FIELDS` must appear in exactly one classification
    - `test_no_overlap_between_classifications` — a field can't be both pruning and scope
    - `test_no_unknown_fields_in_classifications` — classifications can't reference non-Patch field names (catches typos)

  Decoupled from `_PATCH_FIELDS` on purpose — `_PATCH_FIELDS` exists for null rejection in `reject_null_filters`, not warning semantics. The overlap today is coincidence, not contract. The drift test enforces the classification decision at CI without coupling the two concerns.

  Post-change gates:
    - `uv run ruff check` → All checks passed (no PLC0415 after hoisting test imports to top-level)
    - `uv run pytest -x -q` → 2506 passed (97.58% coverage, +3 new tests)

### 6. Behavior: `list_tasks(parent="TaskName")` returns anchor + subtree
expected: Via live MCP client (Claude Code CLI preferred per UAT validator-shadow note), call `list_tasks` with `parent` set to the name of a real parent task in your OF database. Result includes the anchor task itself plus all descendants at any depth (BFS via _collect_task_descendants). Outline order preserved. Pagination works.
result: issue
reported: "Wait, but the flagged it should include the parent. I don't see the parent."
severity: major
notes: |
  Scope-only and reorder cases passed — outline ordering correct after moving the dropped task, sparse order preserved (visible tasks retain absolute outline position), anchor + full subtree returned with no warnings. All consistent.

  Three live probes against "🚀 Build and Ship OmniFocus Operator":
    1. `parent="Build and Ship OmniFocus"` (scope-only) → 5 items, anchor + 4 descendants, outline order preserved, no warnings. PASS.
    2. `parent="Build and Ship OmniFocus", completed="all", dropped="all"` → 7 items (surfaces 2 lifecycle-excluded children), outline order preserved. WARN-01 fired — see Gap G2.
    3. `parent="Build and Ship OmniFocus", flagged=true` → 1 item (the flagged leaf only), anchor missing. WARN-01 fired. See Gap G1.

  Spec-drift fix from Test 1 confirmed live: the FILTERED_SUBTREE_WARNING body surfaces "-- fetch separately" (double-hyphen), matching the code constant.

  Failing test registered (commit b9d72bf8) as xfail(strict=True) to pin the intended behavior per Gap G1.

### 6b. Behavior: outline ordering under filtering (additional live probe)
expected: After reordering children in OmniFocus (moved dropped task above "Add a parent filter"), the filtered result should reflect new order with sparse `order` values for hidden siblings.
result: pass
notes: Verified live. After move, visible child "Add a parent filter" returned with `order: "3.7.1.2"` (was 3.7.1.1), and dropped sibling at `3.7.1.1` is correctly hidden under default availability. Sparse outline ordering preserved — agent reconstructing the tree from `order` can tell a sibling is filtered out.

### 7. Behavior: `list_tasks(parent="ProjectName")` — no anchor + WARN-02
expected: Via live MCP client, call `list_tasks` with `parent` set to a PROJECT name. Result contains only descendant tasks (no anchor — projects aren't tasks). `PARENT_RESOLVES_TO_PROJECT_WARNING` surfaces in `warnings` — pedagogical hint steering the agent toward `project=...` instead. Results otherwise identical to `list_tasks(project="ProjectName")` (D-15 equivalence).
result: pass
notes: |
  Live probe against "🌟✅ Migrate to Omnifocus (or not)". Ran parent and project calls in parallel.

  Both returned 12 byte-identical items (same IDs, same outline order 1 → 1.1 → ... → 3.5). Project ID `dqKlpvE5k7a` absent from both result sets (projects aren't task rows). WARN-02 fired on parent call only; WARN-02 text interpolated the input value verbatim ("Migrate to Omnifocus"), giving the agent a concrete actionable hint. FILTERED_SUBTREE_WARNING did not fire on either (scope-only, no pruning filter).

  G1 gap does not apply to the project-anchor branch — projects don't inject an anchor in the first place, so there's no anchor to preserve under AND composition. G1 is specifically a task-anchor branch issue.

### 8. Behavior: `parent="$inbox"` equivalence with `project="$inbox"`
expected: Via live MCP client, call both `list_tasks(parent="$inbox")` and `list_tasks(project="$inbox")`. Task payloads byte-identical (test_parent_and_project_byte_identical_for_same_project locks this for projects; $inbox route should honor the same contract since both consume into `in_inbox=True` pre-resolution). Cross-side contradictions: `project="$inbox", parent="SomeTask"` raises CONTRADICTORY_INBOX_PROJECT (new in 3-arg form).
result: pass
notes: |
  Three live checks — all pass, with one issue surfaced and fixed inline:

  1. `parent="$inbox"` vs `project="$inbox"` — both returned byte-identical 10-item payloads (same IDs, same outline order, same total: 348, same hasMore: true). D-15 equivalence holds live for the $inbox path.
  2. WARN-02 asymmetry — not fired on either call. Correct: `$inbox` is consumed by resolve_inbox before `_resolve_parent` runs, so WARN-02 (which requires resolved projects) never enters the picture for sentinels.
  3. Cross-side contradiction `project="$inbox", parent="<task>"` — raises as expected.

  Issue surfaced: error text hard-coded "project" wording even when the residual filter was "parent" (undocumented inheritance of D-14 wart from LIST_TASKS_INBOX_PROJECT_WARNING into the two CONTRADICTORY_INBOX_* constants). Fixed inline per Direction B (template filter name into error text):
    - Renamed CONTRADICTORY_INBOX_PROJECT → CONTRADICTORY_INBOX_WITH_REF
    - Both constants now use `{filter}` placeholder; callers format with "project" or "parent" based on which side tripped the gate
    - Existing regression tests migrated to `CONSTANT.format(filter="project")` (byte-identical to the old hard-coded text)
    - New regression tests lock the parent-side templates via `.format(filter="parent")`

  Commit: `5fedf773 fix(57): template filter name into cross-side inbox contradiction errors`

  Post-fix live verification (after MCP server restart to pick up new code):
    - `list_tasks(project="$inbox", parent="<task>")` → "Combining with a 'parent' filter always yields nothing." ✓
    - `list_tasks(parent="$inbox", inInbox=false)` → "'parent=\"$inbox\"' selects inbox tasks, but 'inInbox=false' excludes them." ✓

  D-14 remaining wart — LIST_TASKS_INBOX_PROJECT_WARNING still hard-codes 'project' wording for parent-substring matches. Not addressed in this fix; noted in commit message as a follow-up candidate.

### 9. Behavior: FILTERED_SUBTREE_WARNING fires on combined filters, not on availability
expected: Via live MCP client:
  (a) `list_tasks(project="Work", flagged=true)` — FILTERED_SUBTREE_WARNING surfaces. Text matches the code constant (currently ends with "--", see Test 1).
  (b) `list_tasks(project="Work")` — no warning (scope-only).
  (c) `list_tasks(project="Work", availability=["remaining"])` — NO warning (D-13 exclusion). This is the key test — agents will routinely combine scope + availability, and we don't want the warning spamming them.
  (d) `list_tasks(flagged=true)` — no warning (scope not set).
result: pass
notes: |
  Ran all four probes in parallel against `project="Migrate to Omnifocus"` (12 tasks):
    (a) + `flagged=true` → 0 items + FILTERED_SUBTREE_WARNING. ✓ Fires on query-presence, not on result cardinality — correct pedagogical behavior.
    (b) Scope-only → 3 of 12 items, no warning. ✓
    (c) Scope + `availability=["remaining"]` (the default) → 3 of 12 items, no warning. ✓ D-13 exclusion confirmed.
    (d) `flagged=true` with no scope → 3 items, no warning. ✓ Short-circuit works.

  Test 9 also surfaced Case 1 (completed/dropped false-positive), now RESOLVED inline:
    - Empirically verified via `completed={"before": "2020-01-01"}` that the baseline 5 items are unchanged (0 pre-2020-completed added). Confirmed completed/dropped are purely additive — they never prune.
    - Moved both fields from `_SUBTREE_PRUNING_FIELDS` to `_NON_SUBTREE_PRUNING_FIELDS`. Updated docstrings on both sets to reflect the three-category reality (scope / inclusion / pruning). Added regression test `test_project_with_completed_zero_match_date_does_not_fire` locking the decisive probe.
    - Commit: `2b56955f fix(57): reclassify completed/dropped as non-subtree-pruning`.
    - Post-fix live verification after server restart: the three earlier-spurious cases (completed-zero-match, dropped-zero-match, completed+dropped="all") all now return with no warnings. ✓

  Case 2 (non-default `availability` under-alerting) intentionally deferred — separate design problem (value-aware predicate), handled in end-of-UAT discussion.

### 10. Behavior: PARENT_PROJECT_COMBINED_WARNING fires when both set
expected: Via live MCP client, call `list_tasks(project="Work", parent="Review")`. `PARENT_PROJECT_COMBINED_WARNING` surfaces, regardless of whether the resolved scope-set intersection is empty or not (presence-based per D-13). If a third dimensional filter is added (e.g., `flagged=true`), both WARN-01 and WARN-03 surface, each exactly once.
result: pass
notes: |
  WARN-03 firing behavior verified live. Two probes with disjoint scopes (project="Migrate to Omnifocus", parent="Build and Ship OmniFocus"):
    - `project + parent` → PARENT_PROJECT_COMBINED_WARNING fired. ✓
    - `project + parent + flagged=true` → BOTH WARN-01 and WARN-03 fired, each exactly once. ✓

  Warning-firing contract works as designed — presence-based, independent of intersection outcome.

  TWO additional bugs surfaced and logged as gaps (G2, G3) — the result sizes themselves were wrong:
    - `project + parent` (empty intersection) returned 1624 items. Expected 0.
    - `project + parent + flagged=true` returned 3 unrelated flagged items (not from either scope). Expected 0.
  Root cause: empty `task_id_scope` handled divergently by the two repos + pre-existing "no-match skip" policy from Phase 35.2. See G2 and G3 in Gaps section.

## Summary

total: 10
passed: 9
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "FILTERED_SUBTREE_WARNING guarantees 'resolved parent tasks are always included' — anchor must survive AND-composition with subtree-pruning filters"
  status: resolved
  reason: "live repro: list_tasks(parent='Build and Ship OmniFocus', flagged=true) returned 1 item (the flagged leaf); anchor absent despite warning text's promise"
  severity: major
  test: 6
  gap_id: G1
  root_cause: |
    Service pre-expands scope via get_tasks_subtree (anchor + descendants) and hands `task_id_scope = [anchor_id, desc1, ...]` to the repo. Repo then assembles `WHERE t.persistentIdentifier IN (anchor_id, desc1, ...) AND t.effectiveFlagged = 1` — the anchor PK is in the IN clause but gets pruned by the AND. Applies to any subtree-pruning filter (flagged, tags, due, etc.), not just flagged.
  artifacts:
    - path: src/omnifocus_operator/service/service.py
      issue: _build_repo_query flattens scope set into task_id_scope; no special-case for anchor preservation under AND composition.
    - path: src/omnifocus_operator/repository/hybrid/query_builder.py
      issue: flat IN + AND predicate composition prunes anchor without regard for its anchor status.
    - path: src/omnifocus_operator/agent_messages/warnings.py
      issue: FILTERED_SUBTREE_WARNING text promises "always included"; implementation can't honor it.
  missing:
    - "Anchor-preservation wiring: either OR the anchor IDs with the pruned predicate at the repo (SQL gymnastics + mirror change in bridge_only.py) OR post-assemble the result at the service (simpler, slight perf cost)."
    - "Decision: keep warning text as-is (aspirational, matches future behavior) vs re-word now (matches current behavior). Current choice: keep text, xfail test pins future behavior."
  xfail_test: tests/test_list_pipelines.py::TestListTasksParentFilter::test_list_tasks_parent_with_pruning_filter_preserves_anchor
  xfail_commit: b9d72bf8
  fix_phase: TBD (not in phase 57 scope; design decision for a follow-up)

- truth: "Empty task_id_scope must produce empty result (0 items), not silently fall back to returning all remaining tasks"
  status: resolved
  reason: "live repro: list_tasks(project='Migrate to Omnifocus', parent='Build and Ship OmniFocus') — two known entities with disjoint scope sets — returned 1624 items (entire remaining task set) instead of 0; WARN-03 fired but the result was catastrophically wrong. Second probe adding flagged=true returned 3 unrelated flagged items from across the database, proving both scope filters were skipped."
  severity: major
  test: 10
  gap_id: G2
  root_cause: |
    service/service.py:547 computes task_id_scope = sorted(self._project_scope & self._parent_scope). When sets are disjoint, result is [] (empty list, not None). Downstream divergence:
      - repository/hybrid/query_builder.py:258 — guard `if query.task_id_scope is not None and len(query.task_id_scope) > 0` treats [] identically to None → filter SKIPPED, returns all tasks.
      - repository/bridge_only/bridge_only.py:227 — guard `if query.task_id_scope is not None` applies filter correctly on []  → returns 0 tasks.
    This violates cross-path equivalence (D-15) and produces agent-confusing output (result size exceeds either scope individually).
    Same bug fires for single-scope cases that resolve to empty — e.g., list_tasks(parent='EmptyProjectName') where the project has zero tasks. Not just project+parent intersection.
  artifacts:
    - path: src/omnifocus_operator/service/service.py
      issue: _build_repo_query produces task_id_scope=[] on empty intersection or empty single-scope resolution; hands off to repo without short-circuit.
    - path: src/omnifocus_operator/repository/hybrid/query_builder.py
      issue: "`len > 0` guard on task_id_scope conflates 'empty list' with 'not specified', silently dropping the filter."
    - path: src/omnifocus_operator/repository/bridge_only/bridge_only.py
      issue: Correct behavior today, but diverges from hybrid — cross-path equivalence regression.
    - path: src/omnifocus_operator/agent_messages/warnings.py
      issue: No warning exists for 'scope intersection is empty' or 'scope resolved to zero tasks'; agents get no signal when the empty-scope path is hit.
  missing:
    - "Service-layer short-circuit: when task_id_scope == [], return ListTasksResult(items=[], total=0, has_more=False, warnings=[...]) without calling the repo. Decision lives at the semantic layer; both repos never see the edge case. Preferred over patching either repo — cross-path equivalence becomes automatic rather than test-enforced."
    - "New warning constant SCOPE_INTERSECTION_EMPTY (or similar) — fires when task_id_scope == [] AND both project and parent were set (intersection case). Simpler variant for single-scope-resolves-to-empty."
    - "Regression tests: (a) project+parent disjoint scopes → 0 items + intersection-empty warning; (b) single scope on empty project → 0 items + scope-empty warning. Must cover both hybrid and bridge_only explicitly to pin cross-path equivalence on this edge."
  fix_phase: TBD (recommended: bundle with G3 since both share the 'empty-means-empty' service-layer short-circuit pattern).
  related: G3 (unified no-match = empty semantic) — same short-circuit mechanism may serve both gaps.

- truth: "Name-resolver filters (project, parent, tags) that fail to resolve to any entity must return empty result + 'did you mean?' warning; skip-filter-and-return-all fallback must be removed"
  status: resolved
  reason: "Current behavior (locked by tests test_unresolved_project_skips_filter_with_warning at line 130 and test_list_tasks_parent_filter_no_match at line 1868): when an entity-resolver filter can't find a match, the filter is silently dropped and all tasks are returned with a 'filter skipped' warning. This conflates 'unknown entity' with 'no filter specified' and produces agent-confusing result sizes. Flo intends the UX to be: no match → 0 results + pedagogical 'did you mean?' hint."
  severity: major
  test: 10
  gap_id: G3
  root_cause: |
    Phase 35.2 established the 'skip filter + warn' policy as the no-match semantic for name-resolver filters (D-02e in 35.2 CONTEXT.md). The DISCUSSION-LOG bundled two distinct UX choices — 'pedagogical did-you-mean warning' and 'permissive skip-filter fallback' — into option 2 and logged both as a single decision. Flo's actual intent was only the first (did-you-mean); the fallback came along as a packaging artifact. Phase 57-02 extended the same policy to the new 'parent' filter mirroring 'project' verbatim.
    Net effect: agents typing a name that doesn't resolve see a result size that exceeds their mental model (the filter was supposed to narrow, but the result is everything).
  scope: |
    Applies to ALL THREE name-resolver filters uniformly:
      - project: list_tasks, list_projects
      - parent: list_tasks
      - tags: list_tasks
    Any filter that goes through an entity-name resolver and produces zero matches should short-circuit to empty result.
  behavioral_change: |
    BEFORE: list_tasks(project='Nonexistent') -> all tasks + warning 'filter skipped'
    AFTER:  list_tasks(project='Nonexistent') -> [] + warning 'no match found for project="Nonexistent" ... did you mean: <suggestions if any>'
  preserved_unchanged:
    - "did-you-mean suggestions: fuzzy close-match suggestions still fire when the input is close to a real entity name."
    - "multi-match behavior: resolution to multiple entities still unions their subtrees + fires multi-match warning. This gap is ONLY about zero matches."
    - "ID-exact matching path: IDs that match exactly bypass the resolver entirely; no change."
  artifacts:
    - path: src/omnifocus_operator/service/service.py
      issue: _resolve_scope_filter (and tag-resolver equivalent) return None on no-match, causing downstream filter-skip behavior. Must return empty set instead, so task_id_scope collapses to [] and the service-layer short-circuit (see G2) returns empty result.
    - path: src/omnifocus_operator/agent_messages/warnings.py
      issue: FILTER_NO_MATCH (or equivalent) currently has 'skipped' wording — must be reworded to match new semantic ('no match found; returning empty; did you mean: X, Y, Z?').
    - path: tests/test_list_pipelines.py (lines 130, 1868 + any tags-equivalent)
      issue: Two tests lock current skip-and-return-all behavior; they flip to expect empty result.
    - path: .planning/milestones/v1.3.1-phases/*/CONTEXT.md (D-02e if present)
      issue: Historical decision supersession — document that D-02e has been revisited for Flo's actual intent.
  missing:
    - "Flip return semantic in _resolve_scope_filter (project, parent) and tag-resolver: empty match set → set() instead of None."
    - "Service-layer handling (coupled with G2): task_id_scope == [] short-circuits to empty result + appropriate warning."
    - "Warning constant update: drop 'skipped' wording; reword to 'no match found; returning empty' + preserve did-you-mean suggestions when fuzzy matches exist."
    - "Test flip: test_unresolved_project_skips_filter_with_warning and test_list_tasks_parent_filter_no_match (and any tags analogue) flip from 'all tasks + warning' to '0 items + warning'. Add missing tags-analogue if absent."
    - "Documentation of the supersession: update D-02e reference with a note that Phase 35.2's bundled decision has been unbundled; 'did-you-mean' stays, 'skip + return all' is removed."
  fix_phase: TBD (recommended: bundle with G2; both gaps close via the same 'empty task_id_scope = empty result' service-layer rule).
  related: G2 (empty task_id_scope from intersection or empty scope) — shares the fix mechanism; this gap additionally requires flipping the resolver's empty-match return value and rewording the warning.

- truth: "Non-default `availability` filter (e.g. `['available']`, `['blocked']`) must fire FILTERED_SUBTREE_WARNING when combined with scope; it genuinely prunes the subtree by excluding task-lifecycle states from the 'remaining' bucket"
  status: resolved
  reason: "Current behavior: `list_tasks(project=X, availability=['available'])` narrows the result by excluding blocked tasks, but WARN-01 does not fire. The D-13 exclusion was designed to avoid spamming the warning on the default value (`['remaining']`), but the same exclusion also silences the non-default (actually-pruning) case. Result: agents combining scope + narrowed availability get no pedagogical hint that they may be missing intermediate parents."
  severity: minor
  test: 10
  gap_id: G4
  root_cause: |
    `availability` is a regular `list[AvailabilityFilter] = Field(default=[REMAINING])` on ListTasksQuery -- not a `Patch[T]` field. It is therefore absent from `_PATCH_FIELDS`, absent from `_SUBTREE_PRUNING_FIELDS`, and absent from `_NON_SUBTREE_PRUNING_FIELDS`. The `check_filtered_subtree` predicate iterates `_SUBTREE_PRUNING_FIELDS` using `is_set()` (Patch-semantic); non-Patch fields are silently invisible to the check. D-13's original "exclude availability" intent is implemented by omission rather than by explicit exclusion with rationale, which is both fragile and silences the non-default case along with the default case.
  scope: |
    Applies to the single field `availability` on ListTasksQuery.
    Not scope-creep -- ListProjectsQuery's availability is orthogonal (no parent/project scope combined with it).
  design: |
    Refined shape agreed with Flo in UAT discussion:
      1. Add `availability` to `_SUBTREE_PRUNING_FIELDS` (same classification axis as other pruning fields).
      2. Introduce a new helper `is_non_default(query, field_name) -> bool` that dispatches on field type:
         - Patch[T] field → equivalent to existing `is_set(value)` (value != UNSET).
         - Regular field with concrete default → `value != field_info.default` (read from Pydantic's `model_fields`).
      3. `check_filtered_subtree` iterates `_SUBTREE_PRUNING_FIELDS` using `is_non_default` instead of `is_set(getattr(...))`.
         The scope check (`is_set(query.project) or is_set(query.parent)`) stays unchanged -- both are Patch fields, `is_set` is sufficient and more specific there.
      4. Classification drift test (`TestSubtreePruningFieldsDrift`) broadens to accept non-Patch filter fields in classifications OR adds an auxiliary list of "filter-semantic" non-Patch fields to enforce coverage.
  artifacts:
    - path: src/omnifocus_operator/service/domain.py
      issue: "_SUBTREE_PRUNING_FIELDS lacks 'availability'. `check_filtered_subtree` iteration uses `is_set(getattr(query, f))` which only works for Patch fields."
    - path: src/omnifocus_operator/contracts/base.py
      issue: No generalized `is_non_default(query, field_name)` helper exists; only `is_set` (Patch-specific) is available. New helper lives here or adjacent.
    - path: tests/test_service_domain.py
      issue: "TestCheckFilteredSubtree currently lacks cases for non-default availability; TestSubtreePruningFieldsDrift only enforces Patch field classification."
  missing:
    - "Helper function `is_non_default(query, field_name)` that correctly handles both Patch fields (returns equivalent to `is_set`) and regular fields with concrete defaults (returns `value != default`). Reads defaults from Pydantic `model_fields`."
    - "Add 'availability' to `_SUBTREE_PRUNING_FIELDS`."
    - "Refactor `check_filtered_subtree` pruning iteration to use `is_non_default` instead of `is_set(getattr(...))`. Preserve current scope check signature."
    - "Drift test adjustment: either broaden coverage to all filter-semantic fields (explicit list including non-Patch fields) OR accept that non-Patch fields may be in the pruning set voluntarily. Both approaches must assert `availability` is classified correctly going forward."
    - "Regression tests: (a) `project + availability=['available']` fires FILTERED_SUBTREE_WARNING; (b) `project + availability=['remaining']` (explicit default) does NOT fire; (c) `project + availability=[]` (empty list) fires; (d) repeat (a)–(c) for `parent`; (e) availability alone (no scope) never fires."
  fix_phase: TBD (independent of G2/G3 -- different fix surface, same planner run can bundle all three).
  related: "Orthogonal to G2/G3 but conceptually related -- G4 is about value-aware predicate detection, G2/G3 are about short-circuit semantics. All three could ship in one gap-closing phase if desired."

## Pending discussion (before UAT completes)

_All design discussions resolved. UAT complete._

- ~~G2 candidate — false-positive WARN-01 with `completed="all"` / `dropped="all"`~~ — **RESOLVED** inline during Test 9 (commit `2b56955f`). Empirically verified completed/dropped are inclusion-only, never pruning; reclassified both as `_NON_SUBTREE_PRUNING_FIELDS`; regression test added.
- ~~Case 2 — non-default `availability` under-alerting~~ — **LOGGED AS G4** (above). Refined fix shape agreed: add `availability` to `_SUBTREE_PRUNING_FIELDS` + introduce generalized `is_non_default` helper that dispatches on Patch vs concrete-default fields.

## Mechanical Checks (auto-run — no user action needed)

| Check | Result |
|-------|--------|
| `uv run pytest -x -q` | 2503 passed (97.58% coverage) |
| `uv run pytest tests/test_output_schema.py -x -q` | 35 passed |
| `grep -rn "project_ids" src/ tests/` | 0 matches (grep-0 invariant honored) |
| em-dash positive gate (U+2014 in warnings.py) | no longer applicable — em-dash de-locked intentionally (Test 1) |
| em-dash negative gate (no `--` in warnings.py) | no longer applicable — same |
| Verification report (57-VERIFICATION.md) | 5/5 truths verified; 20/20 requirements satisfied |

## Post-Resolution Gap Audit (2026-04-24)

Retroactive walkthrough confirming the G1–G4 deliveries from 57-04 / 57-05 match the gap descriptions — both behavior and the implementation details agreed in the gap write-ups.

### G1 — Anchor preservation (OR-with-pinned)

Code shape verified:
- `contracts/use_cases/list/tasks.py:130-131` — two-field split: `candidate_task_ids` (filterable pool) + `pinned_task_ids` (unconditional). ✓
- `repository/hybrid/query_builder.py:299-318` — `WHERE pi.task IS NULL AND ((t.id IN <pinned>) OR (<inner_and>))`. Base invariant (`pi.task IS NULL`) sits outside the OR so projects never leak into task results via either branch. ✓
- `repository/bridge_only/bridge_only.py:262-268` — pinned union after the sequential filter chain. ✓

Open discussion — bridge_only ordering:

Initial concern: bridge_only line 268 appends (`items = items + pinned_tasks`) where the hybrid OR puts pinned placeholders first in the params tuple (query_builder.py:315). Closer inspection of line 271 shows `items.sort(key=lambda t: t.id)` runs downstream, so prepend vs append is cosmetic — no user-visible behavioral difference.

Options under consideration:
1. Do nothing — the asymmetry is cosmetic; behavior already deterministic.
2. Prepend for expressive symmetry with hybrid — still a runtime no-op.
3. Remove the `t.id` sort; honor outline order from `all_entities.tasks` — real semantic change: bridge_only would then mirror hybrid's outline ordering more faithfully (not just its membership).

Decision: **#1 — do nothing**. Output is already deterministic; the append-vs-prepend distinction has no observable effect thanks to the downstream `t.id` sort.

### G2 — Empty-scope intersection warning — SUPERSEDED (2026-04-24)

- **What G2 shipped (57-04):** `EMPTY_SCOPE_INTERSECTION_WARNING` — fired only on the narrow `project ∩ parent` disjoint case. See `agent_messages/warnings.py` (pre-retirement) and `service.py::_emit_empty_intersection_warning_if_applicable` (pre-retirement).
- **Why it was incomplete:**
  - Single-scope-empty stayed silent — `list_tasks(parent="EmptyProject")` returned `items=[], warnings=None`, agent couldn't distinguish "filter matched nothing" from "filter matched an empty entity".
  - No-match name cases leaned on `FILTER_NO_MATCH` as a separate narrow warning.
  - Every empty-result shape had its own sibling warning — N narrow warnings, no uniform signal.
- **Decision (2026-04-24):** Unify the entire empty-result warning surface into one parameterized `EMPTY_RESULT_WARNING`. Fires when `items == []` AND any `ListTasksQuery` field is non-default; text is parameterized by active-filter count and lists camelCase aliases alphabetically.
- **Retired:**
  - `EMPTY_SCOPE_INTERSECTION_WARNING` → subsumed.
  - `FILTER_NO_MATCH` → subsumed; `FILTER_DID_YOU_MEAN` reworded to stand alone when fuzzy candidates exist.
- **Two-layer model:**
  - **Layer 1** — unified empty-result warning (this quick task).
  - **Layer 2** — reworded DYM on top when the name had fuzzy candidates.
- **Scope guard:** service-layer only; no contract or repo changes. `list_projects` / `list_folders` / `list_tags` are intentionally out of scope — extending the unified surface to them is a follow-up captured in the quick task SUMMARY.
- **Implementation:** `.planning/quick/260424-j63-unify-empty-result-warning-surface/` (Task 1 commit for src, Task 2 commit for tests). Alphabetical ordering locked by `TestEmptyResultWarning::test_three_plus_active_filters_alphabetical` in `tests/test_list_pipelines.py`.

### G2 — Second iteration (2026-04-24, kd0)

- **What surfaced in live-probe:** Running `list_tasks` against the real OmniFocus MCP surface revealed that pagination and response-shaping fields (`limit`, `offset`, `include`, `only`) were being enumerated by `_active_filter_names` as "filters" in the parameterized warning. Setting `limit=10` on an otherwise-empty query produced a warning text listing `'limit'` as the active filter that resolved to zero tasks — pagination/envelope fields incorrectly classified as scope filters.
- **Decision (2026-04-24):** Collapse the entire parameterization machinery to a single static nudge rather than patching the field-classification predicate. The static text reads: `"The filters you selected didn't yield any results. Try widening the search."`
- **Rationale:** Parameterization carried ~70 LOC of complexity (`_active_filter_names`, two templated constants, `is_non_default` iteration, camelCase alias lookups, alphabetical sort, zero-filter skip, and the 9-case test matrix that locked it all). The agent never semantically parsed the filter list — it saw items=[] and adjusted regardless of which filters were listed. The static nudge is equivalent from the agent's perspective and eliminates the whole field-classification surface. Patching which fields count as "real filters" would have reintroduced the same classification problem whenever a new response-shaping field gets added.
- **Retired (second pass):**
  - `EMPTY_RESULT_WARNING_SINGLE` / `EMPTY_RESULT_WARNING_MULTI` → replaced by single static `EMPTY_RESULT_WARNING`.
  - `_ListTasksPipeline._active_filter_names` helper → deleted.
  - `is_non_default` import in `service.py` → dropped (predicate itself stays — still used by `check_filtered_subtree` for subtree pruning).
  - 8-case parameterized test matrix in `TestEmptyResultWarning` → collapsed to 3 tests (static fires + composes with PARENT_PROJECT, non-empty guard, composes with DYM).
- **Behavior change:** The "zero filters + empty DB" edge case now gets the static nudge too (previously silent). Deliberate loosening — near-impossible in practice, and the uniform signal is simpler than special-casing.
- **Reference:** `.planning/quick/260424-kd0-simplify-empty-result-warning-to-single-/` for full rationale trail (CONTEXT.md §decisions, RESEARCH.md dead-code sweep, PLAN.md single-atomic-task execution).
