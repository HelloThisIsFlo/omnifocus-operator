---
created: 2026-04-18T14:17:00.914Z
title: Remove availability from NEVER_STRIP
area: server
files:
  - src/omnifocus_operator/server/projection.py:21-50
---

## Problem

`NEVER_STRIP` in `projection.py:23` currently contains `{"availability"}`. This is defensive code that does no actual work.

**Why it's dead protection:**
- `availability` is a `StrEnum` with values `"available"`, `"blocked"`, `"completed"`, `"dropped"` (`models/enums.py:84-90`).
- The strip set is `{None, "", False, "none"}` plus empty lists/dicts (`projection.py:21-50`).
- None of the `availability` enum values can ever match the strip set — string `"available"` is not `False`, not `""`, not the literal string `"none"`.
- Therefore `availability` is physically un-strippable today; its presence in `NEVER_STRIP` protects against nothing.

**Why this matters:**
The misleading precedent caused real confusion during the v1.4.1 design conversation. A reader inferring the *why* from `availability`'s membership is led to believe `NEVER_STRIP` exists for "fields where the default value carries meaning" — which is wrong. Once `completesWithChildren` (boolean) joins `NEVER_STRIP` in v1.4.1, it becomes the first field where the mechanism actually does load-bearing work.

## Solution

- Remove `"availability"` from the `NEVER_STRIP` frozenset.
- Add a short docstring/comment on `NEVER_STRIP` explaining what it's for: "Booleans whose `False` value carries meaning and must survive the universal strip-when-false rule."
- Verify no test depends on `availability` being in `NEVER_STRIP` (should be no behavioral change because the enum can't be stripped anyway).

## Context

- Surfaced during v1.4.1 spec interview (2026-04-18) — discussion around adding `completesWithChildren` to `NEVER_STRIP`.
- Spec file: `.research/updated-spec/MILESTONE-v1.4.1.md`
- Interview notes: `.research/updated-spec/MILESTONE-v1.4.1.interview-notes.md`
- Coordinate with v1.4.1 implementation — likely makes sense to clean up at the same time as adding `completesWithChildren` to `NEVER_STRIP`.
