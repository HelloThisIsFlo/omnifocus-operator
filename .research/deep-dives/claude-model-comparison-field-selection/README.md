# Claude Model Comparison — Field Selection

Three Claude models implemented the same feature in parallel: **field selection and null exclusion** for `list_tasks` and `list_projects`. Two external AI reviewers then evaluated the results.

## The Feature

Allow callers to request a subset of fields and exclude null values from list tool responses. Deceptively simple — touches API contracts, schema generation, server/service boundaries, and type honesty.

## Implementations (branches)

Each branch has a single commit with the full implementation:

| Branch | Model | Approach |
|--------|-------|----------|
| `claude-model-comparison-field-selection/opus-4.6` | Opus 4.6 | Projection at server boundary, relaxed output schema, service returns full models |
| `claude-model-comparison-field-selection/opus-4.5` | Opus 4.5 | Projection in service layer, `ProjectedItem` dict-proxy, type-ignore masquerading |
| `claude-model-comparison-field-selection/sonnet-4.6` | Sonnet 4.6 | Projection in service layer, returns `dict[str, Any]`, simpler but weaker schema |

## Reviews

| File | Reviewer | Verdict |
|------|----------|---------|
| `Field Selection Review Codex.md` | OpenAI Codex | Opus 4.6 wins |
| `Field Selection Review Gemini.md` | Google Gemini | Opus 4.6 wins |
| `field-selection-comparison.html` | Visual side-by-side comparison | — |

Both reviewers independently ranked **Opus 4.6 first** for architectural purity (projection as a presentation concern at the server boundary) and schema handling (relaxed output schema preserving type documentation).

## Ranking

1. **Opus 4.6** — best architecture, best schema handling, best caller ergonomics
2. **Sonnet 4.6** — solid and simple, but weakens the response schema
3. **Opus 4.5** — works but service contract becomes dishonest (`type: ignore` on return type)
