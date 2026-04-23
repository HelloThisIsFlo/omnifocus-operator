# Reads Combined Regression Suite

Full regression covering all read-side features: list/filter/search tasks, response shaping (stripping + `include`/`only` + count-only), list projects, simple list tools (tags, folders, perspectives), and cross-tool validation & error formatting. This is a **composite suite** — it references base suites rather than containing tests directly.

## Composite Suite

Run these base suites in order. Each suite keeps its own parent task, setup, and conventions. The runner consolidates discovery, manual actions, and cleanup across all suites.

| Prefix | Suite | File | Tests |
|--------|-------|------|------:|
| A | List Tasks | `list-tasks.md` | 54 |
| B | Date Filtering | `date-filtering.md` | 37 |
| C | Response Shaping | `response-shaping.md` | 14 |
| D | List Projects | `list-projects.md` | 39 |
| E | Simple List Tools | `simple-list-tools.md` | 23 |
| F | Validation & Errors | `validation-errors.md` | 35 |

**Total: 202 tests**

Report table rows use section prefixes (A-1a, B-2a, C-1, D-1a, ...) with bold section-header rows between suites. Each suite's `## Report Table Rows` section provides the row definitions.
