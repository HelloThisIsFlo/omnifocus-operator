---
phase: v1.4.2-until-format-hotfix
reviewed: 2026-05-13T00:00:00Z
depth: deep
files_reviewed: 8
files_reviewed_list:
  - src/omnifocus_operator/repository/rrule/parser.py
  - src/omnifocus_operator/repository/rrule/builder.py
  - tests/test_rrule.py
  - tests/test_service.py
  - tests/test_date_normalization.py
  - uat/capture_golden_master.py
  - CHANGELOG.md
  - README.md
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# v1.4.2 UNTIL Format Hotfix — Code Review

**Reviewed:** 2026-05-13
**Scope:** `2172740c..HEAD` (six commits, golden master snapshot churn excluded)
**Depth:** deep — cross-file trace through parser → adapters → service edit pipeline → builder, plus full sweep for legacy literals

## Summary

Solid, surgical hotfix. Parser tolerance is correctly bidirectional; builder switch to DATE form is clean; round-trip and legacy-tolerance tests anchor the behavior contract. The new regex correctly enforces trailing `Z` on the optional time portion (no new malformed inputs admitted) and the new error message is wired through the right entry point. The UAT validator addition reads the correct raw bridge field. Two findings are documentation-accuracy concerns, three are nits / minor polish.

## Warnings

### WR-01: CHANGELOG claim "first edit of a legacy rule naturally rewrites it" is misleading

**File:** `CHANGELOG.md:17`
**Issue:** The line "First edit of a legacy rule naturally rewrites it to the canonical form" implies that *any* task edit will rewrite the stored ruleString. It won't.

Tracing the edit pipeline:
- `_EditTaskPipeline._apply_repetition_rule` at `src/omnifocus_operator/service/service.py:981` early-returns when `repetition_rule` is UNSET (line 996-997).
- `_assemble_repetition_payload` only builds `RepetitionRuleRepoPayload` when the user explicitly touched the repetition spec (line 1107-1114).
- `BridgeWriteMixin._dump_payload` (`src/omnifocus_operator/repository/bridge_write_mixin.py:44`) only includes `repetitionRule` in the bridge command when it's present in the payload.
- `EditTaskRepoPayload.repetition_rule` (`src/omnifocus_operator/contracts/use_cases/edit/tasks.py:170`) defaults to `None` and the bridge dump excludes unset fields (`exclude_unset=True`).

So a user who edits a task's name/tags/dates a thousand times will never trigger a builder write; the stored DATE-TIME ruleString persists indefinitely. The rewrite only happens on edits that explicitly touch the repetition rule.

**Fix:** Reword to something accurate, e.g.:
```markdown
Pre-1.4.2 rules already stored in user databases (`UNTIL=YYYYMMDDT000000Z`) continue to round-trip cleanly via the new parser tolerance; no migration required. Editing the repetition rule itself rewrites it to the canonical DATE form; otherwise the legacy form persists until OmniFocus or the user touches it.
```

### WR-02: New regex shifts educational error message to stdlib error for some malformed inputs

**File:** `src/omnifocus_operator/repository/rrule/parser.py:32,285`
**Issue:** The new regex `^(\d{4})(\d{2})(\d{2})(?:T\d{6}Z)?$` matches any 8-digit string, including invalid dates like `00000000` or `20269999`. These now pass the regex and fail in `date_type(int(...), int(...), int(...))` with the stdlib message `month must be in 1..12` or similar — not the educational "UNTIL must match YYYYMMDD or YYYYMMDDTHHMMSSZ format" message. Old regex also delegated some out-of-range validation to `date()` (e.g. `20269999T000000Z`), so this is not a new regression; it's the same surface area just re-shaped. Calling it out for completeness — the failure still raises `ValueError`, so callers handle it the same way.

**Fix:** Optional. If you want consistent educational errors, wrap the `date_type(...)` call:
```python
try:
    return date_type(int(m.group(1)), int(m.group(2)), int(m.group(3)))
except ValueError as err:
    raise ValueError(f"UNTIL has out-of-range calendar values: {raw!r} ({err})") from err
```
Otherwise leave as-is and accept that "regex passes, calendar fails" is an acceptable two-stage validation.

## Info

### IN-01: Parser docstring still says "compact" in one neighbouring helper but new prose says "UNTIL value"

**File:** `src/omnifocus_operator/repository/rrule/builder.py:156`
**Issue:** `_convert_date_to_until` docstring still opens with "Convert a date object to RRULE compact UNTIL format." — the word "compact" was meaningful when both forms had `T000000Z`; now "DATE form" or "RFC 5545 DATE form" reads cleaner and matches the parser's own vocabulary.

**Fix:** First line → `"Convert a date object to RRULE UNTIL value (DATE form)."`

### IN-02: `_until_bad_format_message_mentions_both_forms` test entry point is correctly wired

**File:** `tests/test_rrule.py:448-451`
**Issue:** Not a defect — answering your question (3) directly. The test calls `parse_end_condition("FREQ=DAILY;UNTIL=2026-12-31")`. Tracing:
- `parse_end_condition` (`parser.py:115`) calls `_parse_parts` (succeeds — `UNTIL=2026-12-31` is a valid `key=value` pair), then `_validate_end_exclusion` (passes — no COUNT), then enters the `"UNTIL" in parts` branch (line 131-132), then calls `_convert_until_to_date("2026-12-31")` which fails the regex and raises the new educational error.

Wiring is correct, the validation path runs, and the assertion `match="YYYYMMDD or YYYYMMDDTHHMMSSZ"` will fire on the new message. ✅

### IN-03: Sweep for stale `T000000Z` literals is clean in production scope

**File:** (sweep result)
**Issue:** Not a defect — answering question (5). Outside the parser/builder docstrings and the one intentional legacy-tolerance test (`tests/test_rrule.py:401`), I found no surviving `T000000Z` or `YYYYMMDDTHHMMSSZ` literals in `src/`, `tests/` (excluding snapshots), or `uat/`. The only other hits are:
- `.research/deep-dives/rrule-validator/*` — research scratch, deliberately frozen, out of scope
- `.research/deep-dives/repetition-rule/repetition-rule-guide.md:182` — example table in research notes, out of scope
- `CHANGELOG.md` — intentional legacy form reference in the changelog body
- Docstrings in `parser.py` and `builder.py` — intentional legacy form documentation

All production-relevant test fixtures (`test_date_normalization.py:31`, `test_service.py:2240`, `test_rrule.py:564/570/611`, `uat/capture_golden_master.py:1161/1167/1178`) have been migrated to DATE form. `tests/test_repository_repetition_rule.py:93` uses `"UNTIL=" in result["ruleString"]` (substring assertion) — unaffected. `tests/doubles/bridge.py:55` uses key-split dict parsing that doesn't care about the UNTIL format.

## Answers to Your Specific Questions

1. **Regex correctness** — Yes. `^(\d{4})(\d{2})(\d{2})(?:T\d{6}Z)?$` correctly uses a non-capturing group for the optional time portion, correctly enforces a trailing `Z` (the `Z` is *inside* the non-capturing group so it's required only when `T` is present), and is anchored on both ends. No malformed inputs admitted that the old regex rejected — the only newly-accepted inputs are `\d{8}$` (intended) and `\d{8}T\d{6}Z$` with non-midnight times (which the old regex also accepted via the captured-but-discarded HMS groups). One minor surface noted in **WR-02**: out-of-range calendar dates produce stdlib errors instead of educational ones, same as before.

2. **Error message contract** — No callers outside `test_rrule.py:450` assert against the literal "UNTIL must match…" message. I greped for `YYYYMMDD`, `HHMMSS`, and `YYYY-MM-DD` across `src/` and `tests/`; the only matches are the parser source, the parser docstring, the new test, and the CHANGELOG body. The contract change is safe.

3. **Test entry point** — See **IN-02** above. Yes, `parse_end_condition` correctly routes through `_convert_until_to_date` for the test input, so the new error message is actually exercised.

4. **`completedByChildren` field name** — Correct. `src/omnifocus_operator/repository/bridge_only/adapter.py:238` pops `completedByChildren` from raw bridge dicts (and remaps to `completesWithChildren` on the model side). `src/omnifocus_operator/bridge/bridge.js:163,203` writes `completedByChildren`. `tests/conftest.py:63,119` seeds raw bridge fixtures with `completedByChildren`. The validator addition at `uat/capture_golden_master.py:2007` reads the right key.

5. **Stale literal sweep** — See **IN-03** above. Clean in production scope.

6. **CHANGELOG "first edit naturally rewrites" claim** — Inaccurate. See **WR-01** for the trace.

---

_Reviewed: 2026-05-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
