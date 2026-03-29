# Structure Over Discipline

*Designing architecture for agents who always take the shortest path*

---

Design the architecture so the path of least resistance leads to the right outcome. Don't rely on discipline, documentation, or judgment calls at decision time — make the structure itself guide toward the right choice.

## Why agents need paved paths

With human developers, you can afford to watch where they walk and then pave. Humans create legible desire paths — patterns emerge, you observe, you formalize. That's pragmatic and often the right approach.

Agents don't create legible desire paths. They optimize for least resistance uniformly and instantly — there's no signal in the trampling. You can't observe a pattern when "whatever compiled first" is the only pattern. By the time you notice the path was wrong, the grass is gone.

So: pave first. Agents don't create patterns — they just take the shortest path to "it compiles."

## Why YAGNI shifts

Traditional YAGNI says don't build what you don't need. With agents, the cost calculus shifts:

- **Duplication is cheap.** Agents don't get bored maintaining four similar classes. They don't forget to update one of them.
- **Wrong abstractions are expensive.** An agent lacks the context to know it's making the wrong choice — it will happily cram a new field into a shared type or subclass a model that should be independent.
- **Pre-paving a decision pathway costs a paragraph.** An agent getting it wrong costs design debt you have to unwind — and you may not notice until it's entangled.

## Applied in this project

### Type system as guide rails

| Decision | Unguided path | Designed path | Why |
|----------|---------------|---------------|-----|
| Three-way patch semantics (`UNSET` / `None` / value) | Use `None` for both "not provided" and "clear this field" — disambiguate with comments and convention | `Patch[T]` and `PatchOrClear[T]` type aliases + `is_set()` TypeGuard — the type system refuses to compile wrong patterns | Can't accidentally confuse "no change" with "clear" — the types are literally different |
| Separate `AddTaskRepoResult` / `EditTaskRepoResult` | Shared `WriteResult` — identical fields today | One type per operation | When fields diverge, the change is "add a field" not a design decision |
| Write specs always get their own class | Reuse core model — same fields | Dedicated `CommandModel` class | Base class difference (`extra="forbid"`) enforces the boundary automatically |
| `TagRef` / `ParentRef` instead of bare IDs | `tags: list[str]` — just IDs, agent must do extra lookups for names | `tags: list[TagRef]` — repository must populate names at load time | Structure forces complete data; "I'll add names later" can't happen |
| `NounRead` in model taxonomy | Add serializer to core model, or subclass it | Documented pathway: separate Read model, derivable from core | Agent sees the pattern before the need arises — no improvisation |

### Module boundaries as decision guides

| Decision | Unguided path | Designed path | Why |
|----------|---------------|---------------|-----|
| Pipeline pattern (Method Object) for use cases | All logic in `service.add_task()` — service grows to 500+ lines, steps get tangled | `_AddTaskPipeline` with named steps: `_validate()`, `_resolve_parent()`, `_resolve_tags()`, `_build_payload()`, `_delegate()` | Adding logic means extending a step or adding one — sprawl is visible and disruptive |
| `validate.py` vs `domain.py` separation | Single `validate()` function mixing structural checks and business rules | `validate.py` = "is the input structurally valid?" / `domain.py` = "does it make sense in context?" | New check? The module name tells you where it goes |
| `Command` vs `RepoPayload` boundary | Send agent input directly to repository | `AddTaskCommand` (agent-facing, tag names) → service transforms → `AddTaskRepoPayload` (bridge-ready, resolved tag IDs) | Can't accidentally skip resolution — the types are different at each boundary |

## Prior art

This principle exists independently in other domains: **pit of success** in .NET (make it easy to do the right thing), **poka-yoke** in Toyota manufacturing (mistake-proof the process), **desire paths** in urban planning (design around how people actually move). Different domains, same insight: don't fight the actor's nature, design around it.
