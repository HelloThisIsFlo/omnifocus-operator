---
phase: quick
plan: 3
type: execute
wave: 1
depends_on: []
files_modified:
  - .claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py
  - .claude/skills/test-omnifocus-operator/SKILL.md
  - .planning/phases/10-model-overhaul/deferred-items.md
autonomous: true
requirements: []
must_haves:
  truths:
    - "analyze_snapshot.py imports TagAvailability and FolderAvailability (not TagStatus/FolderStatus)"
    - "analyze_snapshot.py uses 'availability' field key for tags and folders (not 'status')"
    - "SKILL.md references TagAvailability/FolderAvailability in enum documentation"
    - "Deferred item is marked as resolved"
  artifacts:
    - path: ".claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py"
      provides: "Updated enum references"
      contains: "TagAvailability"
    - path: ".claude/skills/test-omnifocus-operator/SKILL.md"
      provides: "Updated documentation"
      contains: "TagAvailability"
  key_links:
    - from: ".claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py"
      to: "omnifocus_operator.models.enums"
      via: "importlib import"
      pattern: "enums\\.TagAvailability"
---

<objective>
Fix skill script and documentation references to old enum names (TagStatus/FolderStatus) that were renamed to TagAvailability/FolderAvailability in phase 10.

Purpose: The analyze_snapshot.py script will crash on import because it references enums that no longer exist.
Output: Working script with correct enum references, updated docs, resolved deferred item.
</objective>

<execution_context>
@/Users/flo/.claude/get-shit-done/workflows/execute-plan.md
@/Users/flo/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/10-model-overhaul/deferred-items.md
@.claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py
@.claude/skills/test-omnifocus-operator/SKILL.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update enum references in analyze_snapshot.py and SKILL.md</name>
  <files>
    .claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py
    .claude/skills/test-omnifocus-operator/SKILL.md
    .planning/phases/10-model-overhaul/deferred-items.md
  </files>
  <action>
    In analyze_snapshot.py, make these exact changes:

    1. Line 70: change `"status": values(enums.TagStatus)` to `"availability": values(enums.TagAvailability)`
    2. Line 73: change `"status": values(enums.FolderStatus)` to `"availability": values(enums.FolderAvailability)`

    In SKILL.md, line 126: change `TagStatus, FolderStatus` to `TagAvailability, FolderAvailability`

    In deferred-items.md: add a `- **Status:** Resolved (quick task 3)` line under item 1, or mark it with a strikethrough/resolved note.
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && python -c "import sys; sys.path.insert(0, 'src'); from omnifocus_operator.models.enums import TagAvailability, FolderAvailability; print('enums exist')" && grep -n "TagAvailability" .claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py && grep -n "FolderAvailability" .claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py && grep -n "TagAvailability" .claude/skills/test-omnifocus-operator/SKILL.md && ! grep -n "TagStatus\|FolderStatus" .claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py && ! grep -n "TagStatus\|FolderStatus" .claude/skills/test-omnifocus-operator/SKILL.md && echo "ALL CHECKS PASSED"</automated>
  </verify>
  <done>
    - analyze_snapshot.py references TagAvailability/FolderAvailability with "availability" field key
    - No remaining references to TagStatus or FolderStatus in either file
    - SKILL.md documentation updated
    - Deferred item marked as resolved
  </done>
</task>

</tasks>

<verification>
- `grep -rn "TagStatus\|FolderStatus" .claude/skills/` returns no results
- `grep -n "TagAvailability" .claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py` shows lines 70 and 73
- `grep -n "FolderAvailability" .claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py` shows line 73
</verification>

<success_criteria>
- analyze_snapshot.py imports and uses TagAvailability/FolderAvailability
- Tags dict uses "availability" key (not "status")
- Folders dict uses "availability" key (not "status")
- SKILL.md references new enum names
- Deferred item resolved
</success_criteria>

<output>
After completion, create `.planning/quick/3-fix-deferred-items-from-phase-10-update-/3-SUMMARY.md`
</output>
