"""Could model_fields_set replace UNSET for three-way patch semantics?

Question
--------
Pydantic's `model_fields_set` tracks which fields were explicitly provided
during construction. Could this replace the custom _Unset sentinel for
distinguishing "omitted" (no change) from "null" (clear)?

Current approach (UNSET sentinel)
---------------------------------
    class EditPatch(CommandModel):
        name: Patch[str] = UNSET         # set or omitted
        note: PatchOrClear[str] = UNSET  # set, clear (None), or omitted

    - Field omitted  -> default is UNSET -> no change
    - Field set null  -> None             -> clear value
    - Field set value -> T                -> update

Alternative (model_fields_set)
------------------------------
    class EditPatch(CommandModel):
        name: str | None = None
        note: str | None = None

    - Field omitted   -> not in model_fields_set -> no change
    - Field set null   -> in model_fields_set, value is None -> clear
    - Field set value  -> in model_fields_set, value is T    -> update

This script compares both approaches side-by-side: JSON schema output,
validation behavior, intent detection, error messages, and tradeoffs.

How to run
----------
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && \
    uv run python .research/deep-dives/fastmcp-middleware-validation/4-unset-deep-dive/02_model_fields_set_alt.py
"""

from __future__ import annotations

import json
import textwrap
from typing import Any

from pydantic import AwareDatetime, ValidationError

from omnifocus_operator.contracts.base import (
    UNSET,
    CommandModel,
    Patch,
    PatchOrClear,
    is_set,
)

# ──────────────────────────────────────────────────────────────────────
# 1. Define both models side-by-side
# ──────────────────────────────────────────────────────────────────────


class EditPatchUnset(CommandModel):
    """UNSET-based patch model (current approach)."""

    id: str
    name: Patch[str] = UNSET
    note: PatchOrClear[str] = UNSET
    due_date: PatchOrClear[AwareDatetime] = UNSET


class EditPatchFieldsSet(CommandModel):
    """model_fields_set-based patch model (alternative approach).

    All optional fields default to None. Disambiguation happens via
    model_fields_set, not via sentinel values.
    """

    id: str
    name: str | None = None
    note: str | None = None
    due_date: AwareDatetime | None = None


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

BANNER_WIDTH = 78


def banner(title: str) -> None:
    print(f"\n{'=' * BANNER_WIDTH}")
    print(f"  {title}")
    print(f"{'=' * BANNER_WIDTH}\n")


def sub_banner(title: str) -> None:
    print(f"\n--- {title} ---\n")


def pp_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str)


def describe_intent_unset(model: EditPatchUnset) -> dict[str, str]:
    """Determine intent for each field using UNSET approach."""
    result: dict[str, str] = {}
    for field_name in ("name", "note", "due_date"):
        value = getattr(model, field_name)
        if not is_set(value):
            result[field_name] = "NO CHANGE (UNSET)"
        elif value is None:
            result[field_name] = "CLEAR (None)"
        else:
            result[field_name] = f"UPDATE -> {value!r}"
    return result


def describe_intent_fields_set(model: EditPatchFieldsSet) -> dict[str, str]:
    """Determine intent for each field using model_fields_set approach."""
    result: dict[str, str] = {}
    for field_name in ("name", "note", "due_date"):
        value = getattr(model, field_name)
        if field_name not in model.model_fields_set:
            result[field_name] = "NO CHANGE (not in model_fields_set)"
        elif value is None:
            result[field_name] = "CLEAR (in model_fields_set, value=None)"
        else:
            result[field_name] = f"UPDATE -> {value!r}"
    return result


# ──────────────────────────────────────────────────────────────────────
# 2. Compare JSON schemas
# ──────────────────────────────────────────────────────────────────────

banner("1. JSON SCHEMA COMPARISON")

schema_unset = EditPatchUnset.model_json_schema()
schema_fields_set = EditPatchFieldsSet.model_json_schema()

sub_banner("UNSET-based schema")
print(pp_json(schema_unset))

sub_banner("model_fields_set-based schema")
print(pp_json(schema_fields_set))

sub_banner("Schema differences")
# Compare required fields
print(f"UNSET required:       {schema_unset.get('required', [])}")
print(f"FieldsSet required:   {schema_fields_set.get('required', [])}")
print()

# Compare per-field schemas
for field in ("name", "note", "dueDate"):
    props_u = schema_unset.get("properties", {}).get(field, {})
    props_f = schema_fields_set.get("properties", {}).get(field, {})
    match = "IDENTICAL" if props_u == props_f else "DIFFERENT"
    print(f"  {field}: {match}")
    if props_u != props_f:
        print(f"    UNSET:     {json.dumps(props_u)}")
        print(f"    FieldsSet: {json.dumps(props_f)}")

# ──────────────────────────────────────────────────────────────────────
# 3. Validation behavior comparison
# ──────────────────────────────────────────────────────────────────────

banner("2. VALIDATION BEHAVIOR")

test_cases: list[tuple[str, dict[str, Any]]] = [
    ('All fields omitted:  {"id": "x"}', {"id": "x"}),
    ('Field set:           {"id": "x", "name": "new"}', {"id": "x", "name": "new"}),
    ('Field null:          {"id": "x", "note": null}', {"id": "x", "note": None}),
    (
        'Mixed:              {"id": "x", "name": "new", "note": null}',
        {"id": "x", "name": "new", "note": None},
    ),
]

for label, data in test_cases:
    sub_banner(label)

    # UNSET approach
    m_unset = EditPatchUnset.model_validate(data)
    intent_u = describe_intent_unset(m_unset)

    # model_fields_set approach
    m_fs = EditPatchFieldsSet.model_validate(data)
    intent_fs = describe_intent_fields_set(m_fs)

    print("  UNSET approach:")
    print(f"    model_fields_set = {m_unset.model_fields_set}")
    for k, v in intent_u.items():
        print(f"    {k:15s} -> {v}")

    print()
    print("  model_fields_set approach:")
    print(f"    model_fields_set = {m_fs.model_fields_set}")
    for k, v in intent_fs.items():
        print(f"    {k:15s} -> {v}")

    print()
    same = all(
        intent_u[f].split("(")[0].strip() == intent_fs[f].split("(")[0].strip()
        for f in ("name", "note", "due_date")
    )
    print(f"  Intent matches: {'YES' if same else 'NO -- DIVERGENCE!'}")

# ──────────────────────────────────────────────────────────────────────
# 4. Key question: can model_fields_set distinguish null from omitted?
# ──────────────────────────────────────────────────────────────────────

banner("3. KEY QUESTION: null vs omitted")

print("Can model_fields_set distinguish {\"note\": null} from {}?")
print()

m_omitted = EditPatchFieldsSet.model_validate({"id": "x"})
m_null = EditPatchFieldsSet.model_validate({"id": "x", "note": None})

print(f'  {{"id": "x"}}:')
print(f"    note value:          {m_omitted.note!r}")
print(f"    model_fields_set:    {m_omitted.model_fields_set}")
print(f"    'note' in set:       {'note' in m_omitted.model_fields_set}")
print()
print(f'  {{"id": "x", "note": null}}:')
print(f"    note value:          {m_null.note!r}")
print(f"    model_fields_set:    {m_null.model_fields_set}")
print(f"    'note' in set:       {'note' in m_null.model_fields_set}")
print()

can_distinguish = ("note" not in m_omitted.model_fields_set) and (
    "note" in m_null.model_fields_set
)
print(f"  ANSWER: {'YES' if can_distinguish else 'NO'} -- model_fields_set "
      f"{'CAN' if can_distinguish else 'CANNOT'} distinguish null from omitted")

# ──────────────────────────────────────────────────────────────────────
# 5. Validation errors comparison
# ──────────────────────────────────────────────────────────────────────

banner("4. VALIDATION ERRORS")

invalid_cases: list[tuple[str, dict[str, Any]]] = [
    ("Missing required 'id'", {"name": "oops"}),
    ("Wrong type for name", {"id": "x", "name": 123}),
    ("Invalid date format", {"id": "x", "due_date": "not-a-date"}),
    ("Extra unknown field", {"id": "x", "bogus": True}),
]

for label, data in invalid_cases:
    sub_banner(label)
    print(f"  Input: {data}")
    print()

    for model_cls, approach in [
        (EditPatchUnset, "UNSET"),
        (EditPatchFieldsSet, "model_fields_set"),
    ]:
        try:
            model_cls.model_validate(data)
            print(f"  {approach}: PASSED (no error)")
        except ValidationError as e:
            # Show just the first error for brevity
            err = e.errors()[0]
            print(f"  {approach}: {err['type']} -- {err['msg']}")
    print()


# ──────────────────────────────────────────────────────────────────────
# 6. Bonus: Patch[str] vs str | None -- "name" can't be cleared
# ──────────────────────────────────────────────────────────────────────

banner("5. BONUS: Patch[str] vs PatchOrClear[str] distinction")

print("UNSET approach encodes two different semantics in the type system:")
print("  Patch[str]        -- can set or omit, but CANNOT clear (name)")
print("  PatchOrClear[str] -- can set, clear, or omit (note)")
print()
print("model_fields_set approach uses str | None for both:")
print("  name: str | None = None")
print("  note: str | None = None")
print()
print("This means model_fields_set LOSES the type-level distinction.")
print()

# Show that UNSET approach rejects name=None
sub_banner("UNSET: name=None (should reject)")
try:
    EditPatchUnset.model_validate({"id": "x", "name": None})
    print("  PASSED (unexpected)")
except ValidationError as e:
    err = e.errors()[0]
    print(f"  REJECTED: {err['type']} -- {err['msg']}")

sub_banner("model_fields_set: name=None (will accept)")
m = EditPatchFieldsSet.model_validate({"id": "x", "name": None})
print(f"  ACCEPTED: name={m.name!r}")
print("  -> No way to distinguish 'cannot be cleared' at the type level")

# ──────────────────────────────────────────────────────────────────────
# 7. Verdict
# ──────────────────────────────────────────────────────────────────────

banner("VERDICT")

verdict = textwrap.dedent("""\
    Is model_fields_set viable as an UNSET replacement?

    ANSWER: Technically YES for the core use case, but with real tradeoffs.

    What works:
      - model_fields_set correctly distinguishes "omitted" from "explicitly null"
      - Eliminates UNSET sentinel, Patch/PatchOrClear type aliases, is_set()
      - JSON schema becomes cleaner (no _Unset artifacts to worry about)
      - Standard Pydantic -- no custom __get_pydantic_core_schema__

    What we lose:
      1. TYPE-LEVEL SEMANTICS: Patch[str] vs PatchOrClear[str] distinction
         disappears. Both become str | None. You can no longer tell from the
         type annotation alone whether a field can be cleared. This is the
         biggest loss -- it moves a compile-time / schema-time guarantee to
         a runtime convention.

      2. VALIDATION STRICTNESS: name=None would be accepted by Pydantic
         instead of rejected. You'd need manual validators to re-add this
         constraint ("name was provided but must not be null").

      3. INTENT IS IMPLICIT: With UNSET, intent is in the value itself.
         With model_fields_set, intent requires checking two things (is it
         in the set? what's the value?). Service code goes from:
             if is_set(cmd.name): ...
         to:
             if "name" in cmd.model_fields_set: ...
         Functionally equivalent, but string-based field references are
         less refactor-safe than sentinel checks.

      4. CHANGED_FIELDS() PATTERN: The current CommandModel.changed_fields()
         method works by filtering out UNSET values. With model_fields_set,
         it would filter using model_fields_set -- simpler, but the UNSET
         version is more explicit about intent.

    For the "noise problem" (UNSET appearing in middleware/schema):
      - model_fields_set eliminates the _Unset type from the union entirely
      - JSON schema would be pure str|null -- no sentinel to strip
      - This IS a real advantage if middleware/schema tools choke on UNSET

    Bottom line:
      model_fields_set is a valid alternative that trades type-level
      expressiveness for schema simplicity. The core three-way semantics
      work. But it pushes Patch vs PatchOrClear enforcement from the type
      system to runtime validators -- a meaningful regression in safety for
      a codebase that values strict typing.
""")

print(verdict)
