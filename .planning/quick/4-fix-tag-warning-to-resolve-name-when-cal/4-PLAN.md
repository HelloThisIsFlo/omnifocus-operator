---
phase: quick
plan: 4
type: execute
wave: 1
depends_on: []
files_modified:
  - src/omnifocus_operator/service.py
  - tests/test_service.py
autonomous: true
must_haves:
  truths:
    - "Tag warnings display human-readable name even when caller passes a raw ID"
    - "Warning format is Tag 'HumanName' (tag-id) in all 4 warning sites"
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      provides: "Resolved display names in tag warnings"
    - path: "tests/test_service.py"
      provides: "Tests proving ID-input warnings show resolved names"
  key_links:
    - from: "service.py warning f-strings"
      to: "task.tags / repository.get_tag"
      via: "name lookup before formatting"
      pattern: "Tag '.*' \\(.*\\)"
---

<objective>
Fix tag duplicate/absent warnings to resolve display names when the caller passes a tag ID instead of a name.

Purpose: When callers pass raw tag IDs (e.g. `addTags: ['g4nu27m-aF_']`), warnings currently show the ID in both positions: `Tag 'g4nu27m-aF_' (g4nu27m-aF_)`. Should resolve to `Tag 'Sandbox' (g4nu27m-aF_)`.
Output: Corrected warning messages + tests proving the fix.
</objective>

<execution_context>
@/Users/flo/.claude/get-shit-done/workflows/execute-plan.md
@/Users/flo/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/omnifocus_operator/service.py
@tests/test_service.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Resolve display names in tag warning f-strings</name>
  <files>src/omnifocus_operator/service.py, tests/test_service.py</files>
  <behavior>
    - Test: add_tags with raw ID for tag already on task -> warning shows resolved name, not ID
    - Test: remove_tags with raw ID for tag NOT on task -> warning shows resolved name, not ID
    - Test: add_tags with name string still works as before (regression guard)
  </behavior>
  <action>
Build a display-name helper that maps resolved IDs back to human names. There are two cases across 4 warning sites:

**Add-duplicate warnings (lines 194, 210):** The tag IS on the task. After `_resolve_tags`, build a name map from `task.tags`:
```python
tag_name_map = {t.id: t.name for t in task.tags}
```
Then replace `tag_name` in the f-string with `tag_name_map.get(add_ids[i], tag_name)` to show resolved name when input was an ID.

**Remove-absent warnings (lines 198, 221):** The tag is NOT on the task, so cannot use `task.tags`. Instead, use `all_data.tags` (already loaded in `_resolve_tags` via `get_all()`). But since `_resolve_tags` doesn't expose this, a simpler approach: after `_resolve_tags` returns the resolved IDs, build a reverse lookup by calling `get_all()` once and mapping all tag IDs to names:
```python
all_data = await self._repository.get_all()
all_tag_names = {t.id: t.name for t in all_data.tags}
```
Use this for ALL 4 sites (add-duplicate and remove-absent) to keep it consistent. The `get_all()` call is already cached, so no performance concern.

Place the `all_data` fetch and `all_tag_names` map construction once, just before the first tag warning block (after confirming any tag mode is active). Then at each of the 4 warning sites, replace `tag_name` with `all_tag_names.get(resolved_id, tag_name)`.

Concretely, for each of the 4 sites change:
```python
# Before (line 194 example):
warnings.append(f"Tag '{tag_name}' ({add_ids[i]}) is already on this task")
# After:
display = all_tag_names.get(add_ids[i], tag_name)
warnings.append(f"Tag '{display}' ({add_ids[i]}) is already on this task")
```

Write tests in `tests/test_service.py`:
1. `test_add_tag_warning_resolves_name_from_id` -- add_tags=['tag-x-id'] where tag is already on task, assert warning contains "Tag 'X'" not "Tag 'tag-x-id'"
2. `test_remove_tag_warning_resolves_name_from_id` -- remove_tags=['tag-x-id'] where tag is NOT on task, assert warning contains "Tag 'X'" not "Tag 'tag-x-id'"
3. Existing tests must still pass (name-based input unchanged).
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run pytest tests/test_service.py -x -q</automated>
  </verify>
  <done>All 4 tag warning sites resolve display name from tag ID. Tests prove ID-input warnings show human name. Existing warning tests still pass.</done>
</task>

</tasks>

<verification>
uv run pytest tests/ -x -q  (full suite green)
</verification>

<success_criteria>
- Tag warnings show `Tag 'HumanName' (tag-id)` even when caller passes raw ID
- All existing tests pass
- New tests cover both add-duplicate and remove-absent ID-input cases
</success_criteria>

<output>
After completion, create `.planning/quick/4-fix-tag-warning-to-resolve-name-when-cal/4-SUMMARY.md`
</output>
