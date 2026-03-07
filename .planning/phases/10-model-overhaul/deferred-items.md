# Deferred Items -- Phase 10

## Out-of-scope issues discovered during execution

### 1. Skill script references old enum names (TagStatus, FolderStatus)

- **Found during:** 10-04 Task 2
- **Files:** `.claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py` (lines 70, 73), `SKILL.md` (line 126)
- **Impact:** The snapshot analysis script imports `TagStatus` and `FolderStatus` from `omnifocus_operator.models.enums`. These no longer exist (renamed to `TagAvailability` / `FolderAvailability`). The script will fail on import.
- **Fix:** Update imports and field references in the skill script to use new enum names and `availability` field instead of `status`.
