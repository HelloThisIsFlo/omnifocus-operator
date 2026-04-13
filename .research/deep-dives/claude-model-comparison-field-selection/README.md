# Claude Model Comparison — Field Selection

Three Claude models implemented **field selection + null exclusion** for `list_tasks`/`list_projects` in parallel. Two external AI reviewers evaluated the results independently.

> [!important] Verdict — both reviewers agree
>
> - 🥇 **Opus 4.6** — best architecture, schema handling, caller ergonomics
> - 🥈 **Sonnet 4.6** — solid and simple, weakens the response schema
> - 🥉 **Opus 4.5** — works, but dishonest service contract (`type: ignore` on return type)
>
> Core reason: Opus 4.6 keeps projection at the **transport boundary** instead of leaking it into the service contract.

## Implementations

Each branch has a single commit with the full implementation.

| Branch | Model | Approach |
|--------|-------|----------|
| `…/opus-4.6` | 🥇 Opus 4.6 | Projection at server boundary, relaxed output schema, full models through service |
| `…/sonnet-4.6` | 🥈 Sonnet 4.6 | Projection in service layer, `dict[str, Any]` return — simpler but weaker schema |
| `…/opus-4.5` | 🥉 Opus 4.5 | Projection in service layer, `ProjectedItem` dict-proxy, `type: ignore` masquerading |

> [!note] Branches
>
> - Full prefix: `claude-model-comparison-field-selection/<model>`

## Reviews

| File | Reviewer |
|------|----------|
| [Field Selection Review Codex.md](Field%20Selection%20Review%20Codex.md) | OpenAI Codex |
| [Field Selection Review Gemini.md](Field%20Selection%20Review%20Gemini.md) | Google Gemini |
| [field-selection-comparison.html](field-selection-comparison.html) | Visual side-by-side |
