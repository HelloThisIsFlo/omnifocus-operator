# Closing the Input Schema Gap -- Findings

## The End Game

**Typed params + middleware reformatter.** That's the fully clean end state -- there's nothing beyond it. (This is "Approach 1" in the comparison table below; the other 5 were tested and ruled out or downgraded.)

- `items: list[dict[str, Any]]` → `items: list[AddTaskCommand]` / `items: list[EditTaskCommand]`
- `ValidationReformatterMiddleware` catches validation errors, reformats, raises `ToolError`
- Handlers become trivial: no try/except, no `model_validate()`, just use the typed param
- Agents get rich inputSchema (52-61 fields/enums/refs vs 2 today), auto-generated, always in sync
- Zero regression in error quality. UNSET works cleanly. Validated E2E.

**Caveats (minimal but worth knowing):**
- **Test updates are the bulk of the work** -- tests asserting on validation error paths need updating: errors arrive as `ToolError` (middleware) instead of `ValueError` (handler), and `loc` paths gain an `items.0.` prefix. Mechanical but tedious.
- **Unknown field message diff** -- `Unknown field 'bogusField'` → `Unknown field 'items.0.bogusField'`. Strictly more informative, but differs from today. One-liner fix in `_format_validation_errors` if exact parity matters.
- **Implicit coupling to FastMCP internals** -- relies on validation happening inside `call_next()` (`FunctionTool.run()` → `type_adapter.validate_python()`). If a future FastMCP version moves validation before middleware, the catch wouldn't fire. Unlikely (would be a breaking change), but it's an undocumented internal, not a contract.

Everything below is the evidence trail: what we tested, what we found, why the other 5 approaches don't work or are strictly worse.

## The Gap Today

Agents see this for write tools:
```json
{"items": {"type": "array", "items": {"additionalProperties": true, "type": "object"}}}
```

With typed params, they'd see:
```json
{"items": {"type": "array", "items": {
  "additionalProperties": false, "type": "object",
  "properties": {"name": {"type": "string"}, "dueDate": {"anyOf": [...]}, ...},
  "required": ["name"]
}}}
```

- **Richness score**: typed 52-61 vs untyped 2 (`03_schema_comparison.py`)
- **Schema byte size**: 4-5KB per tool -- well within MCP client limits (`03_schema_comparison.py`)
- **camelCase aliases**: survive all schema generation paths (`01_add_task_schema.py`, `02_edit_task_schema.py`)

## Schema Generation

| Claim | Script | Result |
|-------|--------|--------|
| `AddTaskCommand` generates rich schema with all fields, nested repetition rule, discriminated frequency union | `1-schema-generation/01` | Confirmed |
| `EditTaskCommand` schema cleanly excludes UNSET -- `Patch[str]` -> `{"type": "string"}`, `PatchOrClear[str]` -> `anyOf[string, null]` | `1-schema-generation/02` | Confirmed |
| FastMCP inlines all `$defs`/`$ref` -- no dangling references | `1-schema-generation/01`, `03` | Confirmed (but stale `$ref` paths remain in discriminator `mapping` field) |
| `list[Model]` generates proper `array`-of-object schema with per-item validation | `1-schema-generation/04` | Confirmed |
| `title` fields stripped by FastMCP | `1-schema-generation/01` | Confirmed |

**Surprise:** FastMCP's `DereferenceRefsMiddleware` inlines `$defs` but leaves the discriminator `mapping` field with stale `$ref` paths (e.g., `"daily": "#/$defs/DailyFrequency"`). These paths point to definitions that no longer exist in the inlined schema. Most MCP clients ignore `mapping`, but strict JSON Schema consumers may choke.

## Error Behavior with Typed Params

| Finding | Script |
|---------|--------|
| Middleware catches ALL validation errors from typed params (ValidationError from `type_adapter.validate_python()` inside `FunctionTool.run()`) | `2-error-flow/01` |
| 13 unique error types across both models. Currently handled: 3. Falling through to passthrough: 10 (most are fine as-is) | `2-error-flow/03` |
| UNSET noise is massive: 19 of 49 errors are `is_instance_of` with `_Unset` -- filtering is NOT dead code | `2-error-flow/02` |
| `ctx` dict is rich: `union_tag_invalid` has `expected_tags`, `literal_error` has `expected`, `is_instance_of` has `class: "_Unset"` | `2-error-flow/04` |
| `flagged: "yes"` silently passes (Pydantic lax mode coercion) -- same behavior regardless of approach | `2-error-flow/03` |

**Actionable improvement for `_format_validation_errors`:**
- Filter UNSET noise via `e.get("ctx", {}).get("class") == "_Unset"` instead of fragile `"_Unset" in e["msg"]`
- Use `ctx["tag"]` + `ctx["expected_tags"]` for `union_tag_invalid` instead of manual extraction from `e["input"]`
- Use `ctx["expected"]` for `literal_error` for future-proof lifecycle messages

## The UNSET Question

| Question | Answer | Script |
|----------|--------|--------|
| Is UNSET excluded from JSON schema? | YES -- all 17 tested schema paths (Pydantic, FastMCP inputSchema, outputSchema) | `4-unset-deep-dive/04` |
| Does UNSET noise appear in validation errors? | YES -- every invalid `Patch[T]`/`PatchOrClear[T]` field produces `is_instance_of[_Unset]` noise | `4-unset-deep-dive/01` |
| Can noise be eliminated at source? | YES -- `custom_error_schema` wrapper gives filterable `type="omitted_field_sentinel"` | `4-unset-deep-dive/03` |
| Could `model_fields_set` replace UNSET? | Technically yes, but loses `Patch` vs `PatchOrClear` type-level distinction | `4-unset-deep-dive/02` |
| Does three-way semantics work through typed params? | YES -- omit/null/value all behave correctly | `5-integration/02` |

**UNSET `PydanticJsonSchemaWarning`:** Pydantic emits `Default value UNSET is not JSON serializable; excluding default from JSON schema`. This is expected and correct -- UNSET defaults are excluded, making all Patch fields optional in the schema.

## Approach Comparison

Six approaches were tested. Approach 1 is the end game. Approach 2 is a low-risk stepping stone. The rest are ruled out.

| # | Approach | Schema | Errors | Verdict |
|---|----------|--------|--------|---------|
| **1** | **Typed params + middleware reformatter** | Rich (auto) | Clean (reformatted) | **THE END GAME** |
| 2 | on_list_tools schema injection | Rich (injected) | Clean (unchanged handlers) | Stepping stone to #1 |
| 3 | model_validator(mode="wrap") | Rich (auto) | Noisy -- Pydantic re-wraps | Dead end |
| 4 | Custom FunctionTool subclass | Rich (auto) | Clean (reformatted) | Works but worse than #1 |
| 5 | Built-in ErrorHandlingMiddleware | N/A | Raw dumps, wrong error code | Not suitable |
| 6 | Pydantic custom errors | N/A | Improved filtering only | Complement to #1 |

### Approach 1: Typed Params + Middleware Reformatter (THE END GAME)
- `ValidationReformatterMiddleware.on_call_tool()` wraps `call_next()`, catches `ValidationError`, calls `_format_validation_errors()`, raises `ToolError`
- Handler becomes trivial: no try/except, no `model_validate()`, just use the typed param directly
- Error parity: 10/12 exact match with current output; 2 differences are `items.0.` prefix in unknown-field paths (more informative, not a regression)
- Full E2E validated: `5-integration/01` (12/12), `5-integration/02` (15/15), `5-integration/03` (10/12)
- Script: `3-approaches/01`

### Approach 2: on_list_tools Schema Injection (HYBRID)
- Keep `list[dict[str, Any]]` signature; override `inputSchema` at list time via `on_list_tools` middleware
- Schema generated from `TypeAdapter(list[AddTaskCommand]).json_schema()`
- Handler code unchanged -- manual `model_validate()` + `_format_validation_errors()` stays
- **Pro**: zero handler changes, exact error parity
- **Con**: schema and validation are decoupled -- schema says "name required" but framework doesn't enforce it (handler does)
- **Use case**: incremental first step before full migration to approach 1
- Script: `3-approaches/02`

### Approach 3: model_validator(mode="wrap") -- DEAD END
- Pydantic re-wraps `ValueError` from wrap validator into a new `ValidationError` with `type=value_error`
- Client sees full Pydantic error envelope, not clean message
- Double "Value error" prefix for nested model validators
- Script: `3-approaches/03`

### Approach 4: Custom FunctionTool Subclass
- Override `run()` to catch `ValidationError` and reformat
- Works mechanically, but: per-tool manual registration (no `@mcp.tool`), medium coupling to FastMCP internals (`from_function` using `cls()`, `mcp.add_tool()` API)
- Same `items.0.` loc prefix as approach 1
- Script: `3-approaches/04`

### Approach 5: Built-in ErrorHandlingMiddleware -- NOT SUITABLE
- Maps `ValidationError` to `-32603` (Internal error) instead of `-32602` (Invalid params)
- Dumps raw `str(error)` -- all 19 UNSET noise errors leak through
- `error_callback` is fire-and-forget, cannot modify the error
- Operates at `on_message` level -- catches ALL methods, not just write tools
- Script: `3-approaches/05`

### Approach 6: Pydantic Custom Errors (Complement)
- Can improve `_Unset` noise filtering: `custom_error_schema` → `type="omitted_field_sentinel"` (match on type, not string)
- Cannot eliminate `_format_validation_errors` -- post-processing inherently needed for `extra_forbidden`, `union_tag_invalid`, `literal_error` rewrites
- `model_validator(mode="before")` for extra field rejection is worse than `extra="forbid"`: short-circuits, reports only first problem
- Script: `3-approaches/06`, `4-unset-deep-dive/03`

## Implementation: What Changes

### The End Game (Approach 1)

**What changes:**
1. **New middleware**: `ValidationReformatterMiddleware` in `middleware.py`
   - `on_call_tool`: catch `ValidationError` → `_format_validation_errors()` → `ToolError`
2. **Handler signatures**: `items: list[dict[str, Any]]` → `items: list[AddTaskCommand]` / `items: list[EditTaskCommand]`
3. **Handler bodies**: remove try/except + `model_validate()` block. Use typed `items[0]` directly.
4. **`_format_validation_errors`**: stays in `server.py`, used by the middleware. Optionally improve:
   - Filter `_Unset` via `ctx.get("class")` instead of string matching on msg
   - Use `ctx["expected_tags"]` for `union_tag_invalid`

**What doesn't change:**
- Command models (`AddTaskCommand`, `EditTaskCommand`) -- untouched
- `_Unset`, `Patch[T]`, `PatchOrClear[T]` -- untouched
- Agent-facing error messages -- 10/12 identical, 2 improved
- Service layer -- untouched
- Tool docstrings -- stay (FastMCP uses them for tool description)

**Migration path:**
1. Add `ValidationReformatterMiddleware` (one file)
2. Change `add_tasks` signature + remove try/except (surgical)
3. Change `edit_tasks` signature + remove try/except (surgical)
4. Update tests that check validation error paths
5. Optionally: improve `_format_validation_errors` with ctx-based filtering

### Optional Enhancement: Custom UNSET Error Type

Change `_Unset.__get_pydantic_core_schema__` to use `custom_error_schema` wrapper:
```python
return core_schema.custom_error_schema(
    core_schema.is_instance_schema(cls),
    custom_error_type="omitted_field_sentinel",
    custom_error_message="This field was omitted (no change)",
)
```
Then filter in `_format_validation_errors` via `e["type"] == "omitted_field_sentinel"` instead of `"_Unset" in e["msg"]`.

### Stepping Stone (Approach 2) -- Optional

If the handler refactor feels too large for one phase, deploy approach 2 first as a zero-risk schema improvement:
1. Add `SchemaInjectionMiddleware` with `on_list_tools` (one file)
2. No handler changes at all
3. Agents immediately get rich schemas
4. Later: migrate to approach 1 for full cleanup

## Gotchas

1. **Broken `$ref` in discriminator mapping** -- FastMCP inlines `$defs` but leaves stale `#/$defs/DailyFrequency` paths in the discriminator `mapping` field. Most clients ignore this, but worth noting. (Script: `1-schema-generation/01`)

2. **`items.0.` loc prefix** -- With `list[Model]` params, Pydantic error locations include the list index path (`items`, `0`, `fieldName`). The current path is just `fieldName`. This affects the "Unknown field" message formatting. The prefix is accurate and arguably better, but differs from today's output. (Script: `5-integration/03`)

3. **Pydantic lax mode coercion** -- `flagged: "yes"` silently passes as `True`. This is existing behavior regardless of approach. `strict_input_validation=True` on FastMCP would add JSON Schema pre-validation, but may be too strict for agent use. (Script: `2-error-flow/03`)

4. **`PydanticJsonSchemaWarning`** -- UNSET defaults trigger `Default value UNSET is not JSON serializable; excluding default from JSON schema`. Expected and correct. Suppress with `warnings.filterwarnings("ignore", category=PydanticJsonSchemaWarning)` if noisy. (Script: `1-schema-generation/02`)

5. **Schema size is fine** -- Largest schema (`EditTaskCommand`) is ~5.3KB. Even with all tools, total schema payload is under 15KB. No MCP client limit concerns. (Script: `1-schema-generation/03`)

6. **No `input_schema` parameter on `@tool()`** -- FastMCP does not support raw schema override via decorator. The only path to rich schemas is typed parameters or `on_list_tools` middleware injection. (Context7 research)

7. **`ErrorHandlingMiddleware` exists but is useless for this** -- It's a generic error mapper, not a validation reformatter. Wrong error codes, raw dumps, can't modify errors via callback. (Script: `3-approaches/05`)
