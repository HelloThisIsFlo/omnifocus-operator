# Writes Combined Regression Suite

Full regression covering all write-side features: lookups, task creation, field editing, tags, moves, lifecycle, inheritance, integration flows, and repetition rules. This is a **composite suite** — it references base suites rather than containing tests directly.

## Composite Suite

Run these base suites in order. Each suite keeps its own parent task, setup, and conventions. The runner consolidates discovery, manual actions, and cleanup across all suites.

| Prefix | Suite | File | Tests |
|--------|-------|------|------:|
| A | Read Lookups | `read-lookups.md` | 9 |
| B | Task Creation | `task-creation.md` | 17 |
| C | Edit Operations | `edit-operations.md` | 23 |
| D | Tag Operations | `tag-operations.md` | 15 |
| E | Move Operations | `move-operations.md` | 23 |
| F | Lifecycle | `lifecycle.md` | 12 |
| G | Inheritance | `inheritance.md` | 8 |
| H | Integration Flows | `integration-flows.md` | 8 |
| I | Repetition Rules | `repetition-rules.md` | 40 |

**Total: 155 tests**

Report table rows use section prefixes (A-1, B-2a, C-3, ...) with bold section-header rows between suites. Each suite's `## Report Table Rows` section provides the row definitions.
