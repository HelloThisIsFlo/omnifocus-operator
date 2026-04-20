# Golden Master Snapshots

Captured JSON fixtures for the bridge contract tests. See the parent
[`../README.md`](../README.md) for the canonical capture-and-replay workflow,
normalization categories, and regeneration procedure.

Golden master capture / refresh is **human-only** per project CLAUDE.md feedback:

> "Golden master snapshots are human-only — agents create test infra, never capture/refresh snapshots."

## Subfolder layout

Numbered subfolders are discovered in sort order by
`tests/test_bridge_contract.py::_load_scenarios`. Each subfolder groups scenarios
captured against the real Bridge via `uat/capture_golden_master.py`:

```
snapshots/
  initial_state.json
  01-add/                    (7 scenarios)
  02-edit/                   (10 scenarios)
  03-move/                   (9 scenarios)
  04-tags/                   (5 scenarios)
  05-lifecycle/              (6 scenarios)
  06-combined/               (5 scenarios)
  07-inheritance/            (8 scenarios)
  08-repetition/             (38 scenarios)
  09-task-property-surface/  (Phase 56 field surface — human capture pending)
```

## 09-task-property-surface/ (pending human capture)

New subfolder for the Phase 56 read surface: `completesWithChildren`, `type`,
`hasNote`, `hasRepetition`, `hasAttachments`, `isSequential`,
`dependsOnChildren`, and the expanded `hierarchy` include group. Scenarios are
already declared in `uat/capture_golden_master.py`; fixtures land here the next
time the human runs the capture procedure. Until then the subfolder is empty
and the bridge contract test skips the new scenarios cleanly — same skip-when-
absent contract every numbered subfolder followed before its first capture.
