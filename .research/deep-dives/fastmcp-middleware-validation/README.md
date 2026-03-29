# Deep Dive: FastMCP Middleware Validation

Research spike investigating how to close the input schema gap for write tools (`add_tasks`, `edit_tasks`).

**Problem:** Write tools use `items: list[dict[str, Any]]`, so agents see zero schema info. Read tools have full typed schemas.

**Answer:** Switch to typed params (`items: list[AddTaskCommand]`) + middleware error reformatting. See [FINDINGS.md](FINDINGS.md).

## How to Run

All scripts run from the project root:
```bash
cd /path/to/omnifocus-operator
uv run python .research/deep-dives/fastmcp-middleware-validation/<path-to-script>.py
```

No OmniFocus database access needed. Pure FastMCP/Pydantic research.

## Story Arc

1. **Schema generation** -- What would agents see with typed params?
2. **Error flow** -- What happens when validation fails? Is UNSET noise still a problem?
3. **Approaches** -- 6 approaches tested, only 2 viable
4. **UNSET deep dive** -- Can we eliminate noise at the source?
5. **Integration** -- End-to-end validation of the winning approach

## Directory Structure

```
fastmcp-middleware-validation/
├── README.md                           # This file
├── FINDINGS.md                         # Decision document (the deliverable)
├── middleware_validation_spike.py       # Original proof-of-concept
│
├── 1-schema-generation/                # "What would agents see?"
│   ├── 01_add_task_schema.py           # AddTaskCommand -> inputSchema
│   ├── 02_edit_task_schema.py          # EditTaskCommand (UNSET/Patch) -> inputSchema
│   ├── 03_schema_comparison.py         # dict vs typed: richness score, byte size
│   └── 04_list_wrapper_behavior.py     # list[Model] array schema + per-item validation
│
├── 2-error-flow/                       # "What happens when validation fails?"
│   ├── 01_middleware_intercepts.py     # Middleware catches typed-param errors (real models)
│   ├── 02_unset_noise_catalog.py       # UNSET noise: 19 of 49 errors are _Unset artifacts
│   ├── 03_error_types_real_models.py   # Full catalog: 13 error types, only 3 handled
│   └── 04_error_context_richness.py    # ctx dict: expected_tags, expected, class fields
│
├── 3-approaches/                       # "How can we format errors?"
│   ├── 01_middleware_reformatter.py    # RECOMMENDED -- middleware + typed params
│   ├── 02_on_list_tools_schema.py      # Hybrid -- schema injection, handlers unchanged
│   ├── 03_model_validator_wrap.py      # DEAD END -- Pydantic re-wraps ValueError
│   ├── 04_custom_function_tool.py      # Works but higher coupling than middleware
│   ├── 05_error_handling_middleware.py  # NOT SUITABLE -- wrong codes, raw dumps
│   └── 06_pydantic_custom_errors.py    # Complement only -- can't replace post-processing
│
├── 4-unset-deep-dive/                  # "Can we fix UNSET noise at the source?"
│   ├── 01_unset_in_union_errors.py     # Why _Unset noise exists (union branch errors)
│   ├── 02_model_fields_set_alt.py      # model_fields_set: viable but loses type safety
│   ├── 03_custom_core_schema.py        # custom_error_schema: clean filterable type
│   └── 04_json_schema_exclusion.py     # UNSET excluded from all 17 schema paths
│
└── 5-integration/                      # "Does it work end-to-end?"
    ├── 01_typed_add_tasks_e2e.py       # add_tasks: 12/12 scenarios pass
    ├── 02_typed_edit_tasks_e2e.py       # edit_tasks: 15/15 scenarios pass, UNSET works
    └── 03_error_parity_test.py          # Old vs new: 10/12 match, 2 improved
```

## Key Numbers

| Metric | Value |
|--------|-------|
| Scripts written | 21 (20 new + 1 existing spike) |
| Total test scenarios | 60+ |
| Schema richness (typed) | 52-61 properties/enums/refs |
| Schema richness (dict) | 2 |
| Schema size (largest) | 5.3KB |
| Error parity | 10/12 exact, 2 improved |
| Approaches tested | 6 |
| Approaches viable | 2 (middleware reformatter, schema injection) |
| UNSET noise errors | 19 of 49 (filtered cleanly) |
