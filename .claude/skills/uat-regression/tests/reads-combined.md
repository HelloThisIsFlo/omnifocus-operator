# Reads Combined Regression Suite

Full regression covering all read-side features: list/filter/search tasks, list projects, simple list tools (tags, folders, perspectives), and cross-tool validation & error formatting. This is a **composite suite** — it references base suites rather than containing tests directly.

## Composite Suite

Run these base suites in order. Each suite keeps its own parent task, setup, and conventions. The runner consolidates discovery, manual actions, and cleanup across all suites.

| Prefix | Suite | File | Tests |
|--------|-------|------|------:|
| A | List Tasks | `list-tasks.md` | 46 |
| B | Date Filtering | `date-filtering.md` | 32 |
| C | List Projects | `list-projects.md` | 33 |
| D | Simple List Tools | `simple-list-tools.md` | 23 |
| E | Validation & Errors | `validation-errors.md` | 35 |

**Total: 169 tests**

Report table rows use section prefixes (A-1a, B-2a, C-1, D-1a, ...) with bold section-header rows between suites. Each suite's `## Report Table Rows` section provides the row definitions.
