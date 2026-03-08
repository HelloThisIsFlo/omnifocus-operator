---
status: resolved
trigger: "ISSUE-4: Tool description doesn't declare field boundaries"
created: 2026-03-08T00:00:00Z
updated: 2026-03-08T02:00:00Z
---

## Current Focus

hypothesis: add_tasks docstring lists supported fields but never states they are the ONLY fields; agents cannot infer boundaries
test: Read docstring and model definition, compare
expecting: No boundary language in docstring; Pydantic silently drops extras
next_action: Report diagnosis

## Symptoms

expected: Agent should know that fields like repetition rules, notifications, sequential/parallel settings are NOT supported, so it can inform the user or adjust its approach
actual: Docstring says "Each item accepts:" followed by a field list — no mention that unlisted fields are unsupported and will be silently ignored
errors: No runtime error — Pydantic default `extra="ignore"` silently drops unknown fields
reproduction: Send add_tasks with an unsupported field (e.g. `repetitionRule`); it succeeds but the field is silently dropped
started: Since add_tasks was introduced (phase 15-03)

## Eliminated

(none — diagnosis was straightforward)

## Evidence

- timestamp: 2026-03-08
  checked: server.py add_tasks docstring (lines 152-168)
  found: |
    Docstring says "Each item accepts:" then lists 9 fields.
    No language like "only these fields are supported" or "other fields are not supported and will be ignored."
  implication: An agent reading the tool description cannot distinguish "these are the fields I chose to document" from "these are the ONLY fields available"

- timestamp: 2026-03-08
  checked: models/write.py TaskCreateSpec (lines 18-34)
  found: |
    TaskCreateSpec defines exactly 9 fields: name, parent, tags, due_date, defer_date, planned_date, flagged, estimated_minutes, note.
    Inherits from OmniFocusBaseModel which does NOT set `extra = "forbid"`.
  implication: Pydantic v2 default is `extra="ignore"` — unknown fields are silently dropped without error

- timestamp: 2026-03-08
  checked: models/base.py OmniFocusBaseModel (lines 21-33)
  found: |
    ConfigDict has alias_generator, validate_by_name, validate_by_alias.
    No `extra` setting at all.
  implication: Confirms silent-ignore behavior for all models inheriting from this base

- timestamp: 2026-03-08
  checked: Notable OmniFocus features NOT in TaskCreateSpec
  found: |
    Missing from write model (intentionally, per spec):
    - repetitionRule (repeat/defer intervals)
    - notification/reminder settings
    - sequential/parallel task ordering
    - completion/drop status
    - attachments
    These are features an agent might reasonably attempt to set.
  implication: Without boundary declaration, agent will attempt these and they'll silently vanish

## Resolution

root_cause: |
  Two complementary gaps:
  1. **Docstring gap**: The add_tasks tool description says "Each item accepts:" but never
     declares these are the ONLY supported fields. An agent cannot infer a closed boundary
     from a list — it could be a partial listing of highlights.
  2. **Silent drop**: TaskCreateSpec inherits Pydantic's default `extra="ignore"`, so
     unknown fields are silently discarded. No error, no warning. An agent that sends
     `repetitionRule` gets a success response with no indication the field was ignored.

  Together: agent doesn't know the boundary AND gets no feedback when crossing it.

fix: (not applying — diagnosis only)
verification: n/a
files_changed: []
