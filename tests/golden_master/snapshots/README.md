# Golden Master Snapshots — Capture Procedure

Golden master capture / refresh is **human-only** per project CLAUDE.md feedback:

> "Golden master snapshots are human-only — agents create test infra, never capture/refresh snapshots."

Agents and CI must never set `GOLDEN_MASTER_CAPTURE`. An invariant test in the golden-master module asserts the env var is unset during regular runs, so a misbehaving agent that tries to capture will fail loudly before touching any baseline file.

## Available baselines

| Baseline | Purpose | Generating test |
|----------|---------|-----------------|
| `task_property_surface_baseline.json` | Phase 56 task property surface read shape — `completesWithChildren`, `type`, `hasNote`, `hasRepetition`, `hasAttachments`, `isSequential`, `dependsOnChildren`, and the expanded `hierarchy` include group (parent, `hasChildren`, `type`, `completesWithChildren`) | `tests/golden_master/test_task_property_surface_golden.py::TestTaskPropertySurfaceGoldenMaster::test_task_property_surface_matches_golden_baseline` |

Separate from the scenario-replay fixtures in `01-add/ … 08-repetition/` (those are bridge-contract snapshots captured from the real Bridge; see `../README.md`). The baselines listed above are **service-level** read-shape contracts built from the full OperatorService stack against `InMemoryBridge`.

## Capture procedure — `task_property_surface_baseline.json`

Run manually, with the capture env var set:

```bash
GOLDEN_MASTER_CAPTURE=1 uv run pytest tests/golden_master/test_task_property_surface_golden.py::TestTaskPropertySurfaceGoldenMaster::test_task_property_surface_matches_golden_baseline -x -s --no-cov
```

The test will:

1. Build the current serialized payload from the test service stack.
2. Normalize volatile fields (`id`, `url`, `added`, `modified` → `"<normalized>"`).
3. Write the normalized payload to `task_property_surface_baseline.json` as pretty-printed JSON with sorted keys.
4. Skip itself with a confirmation message so you know capture ran instead of comparison.

Note that the invariant test `test_golden_master_capture_mode_is_opt_in` will FAIL while `GOLDEN_MASTER_CAPTURE` is set — that is by design. Capture is a one-shot human action, not a suite-wide mode. Unset the env var immediately after capture.

## Review + commit procedure

After capture:

1. Inspect the generated `task_property_surface_baseline.json`:
   - No real task data — the seed uses the literal name `"Golden Task"` and a minimal note.
   - No user identifiers — IDs and URLs are `"<normalized>"`.
   - No timestamps — `added` / `modified` are `"<normalized>"`.
2. Commit the baseline with a descriptive message:

   ```bash
   git add tests/golden_master/snapshots/task_property_surface_baseline.json
   git commit -m "test(golden): capture task property surface baseline for v1.4.1 Phase 56"
   ```

3. Re-run the suite WITHOUT the env var to confirm the comparison test now runs green:

   ```bash
   uv run pytest tests/golden_master/test_task_property_surface_golden.py -x --no-cov
   ```

## Refresh procedure

Same as capture — `GOLDEN_MASTER_CAPTURE=1 …` overwrites the existing baseline. **Review the diff carefully before committing**:

```bash
git diff tests/golden_master/snapshots/task_property_surface_baseline.json
```

If the diff reflects intentional shape changes (new field, rename, semantics change), commit with a message explaining what changed and why. If the diff is unexpected, the regression is in code — roll the baseline back and fix the code.

## Rules

- **Agents MUST NOT run `GOLDEN_MASTER_CAPTURE=1`.** The env-var branch is intentionally opt-in and must only be invoked by the human developer.
- **CI MUST NOT set this env var.** Baseline files are committed to the repo; they are part of the test contract.
- **Normalization is deterministic.** The normalization function strips only `id` / `url` / `added` / `modified`. Other volatility in the payload (e.g., new non-deterministic fields) requires normalization to be extended before a stable baseline can be captured.
- **One baseline per shape contract.** When a new read-shape contract needs a golden-master lock, add a new baseline and a new test, not a variant of an existing baseline.
