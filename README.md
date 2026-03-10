# 🎯 OmniFocus Operator

**The last OmniFocus MCP Server you'll ever need.**

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white)
![Tests 534](https://img.shields.io/badge/tests-534-brightgreen)
![Coverage 94%](https://img.shields.io/badge/coverage-94%25-brightgreen)
![Dependencies 1](https://img.shields.io/badge/deps-1-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

Production-grade MCP server exposing OmniFocus as structured task infrastructure for AI agents. Agent-first design, SQLite-cached performance, 534 tests.

### [**→ See the full landing page**](https://hellothisisflo.github.io/omnifocus-operator) — features, architecture, benchmarks, and comparison

---

## 🚀 Quick Start

**Prerequisites:** macOS, OmniFocus 4, Python 3.12+

**Install:**

> **Note:** PyPI/pipx publishing is coming soon. For now, install from source:

```bash
git clone https://github.com/HelloThisIsFlo/omnifocus-operator.git
cd omnifocus-operator
uv sync
```

**Claude Desktop config** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "omnifocus-operator": {
      "command": "omnifocus-operator"
    }
  }
}
```

That's it. The server auto-detects your OmniFocus database and starts serving.

---

## ✨ Features

- ⚡ **46ms reads** via SQLite caching (30–60x faster than bridge-only)
- 🏗️ **Three-layer architecture** — MCP Server → Service → Repository
- 🤖 **Agent-first design** — warnings and guidance built into every response
- 🧪 **534 tests, 94% coverage**, strict mypy
- 🛡️ **Graceful degradation** — server stays alive, errors educate
- 📦 **Single runtime dependency** (`mcp>=1.26.0`)
- 🔄 **Automatic fallback** — SQLite → OmniJS bridge when needed

---

## 🛠️ Available Tools

| Tool | Description | Type |
|------|-------------|------|
| `get_all` | Return the full OmniFocus database as structured data | Read |
| `get_task` | Look up a single task by its ID | Read |
| `get_project` | Look up a single project by its ID | Read |
| `get_tag` | Look up a single tag by its ID | Read |
| `add_tasks` | Create tasks in OmniFocus | Write |
| `edit_tasks` | Edit existing tasks using patch semantics | Write |

All read tools are idempotent. Write tools support full field control including tags, dates, flags, notes, and task movement.

---

## 🔍 Tool Examples

**Create a task** (`add_tasks`):

```json
{
  "items": [{
    "name": "Review Q3 roadmap",
    "parent": "pJKx9xL5beb",
    "tags": ["Work", "Planning"],
    "dueDate": "2026-03-15T17:00:00Z",
    "flagged": true,
    "estimatedMinutes": 30,
    "note": "Focus on v1.3-v1.5 milestones"
  }]
}
```

**Edit with patch semantics** (`edit_tasks`):

```json
{
  "items": [{
    "id": "oRx3bL_UYq7",
    "addTags": ["Urgent"],
    "dueDate": null,
    "moveTo": {"ending": "pJKx9xL5beb"}
  }]
}
```

**Patch semantics cheat sheet:**

| Input | Meaning |
|-------|---------|
| Field omitted | No change |
| Field set to `null` | Clear the value |
| Field set to a value | Update |

---

## 🏗️ What Makes This Different?

- ⚡ **46ms reads** — SQLite caching gives you 30–60x faster reads than bridge-only servers
- 🧪 **534 tests, 94% coverage** — strict mypy, no corners cut
- 🤖 **Agent-first design** — warnings that teach, errors that educate, guidance in every response
- 🛡️ **Degraded mode** — server stays alive no matter what, always recoverable
- 📦 **Single runtime dependency** — just `mcp>=1.26.0`, nothing else

See the [full documentation](https://hellothisisflo.github.io/omnifocus-operator) for architecture details, examples, and deep dives.

---

## 🗺️ Roadmap

| Version | Focus |
|---------|-------|
| **v1.0** | Foundation — read tools, three-layer arch, test suite ✅ |
| **v1.1** | Performance — SQLite caching, 30–60x speedup ✅ |
| **v1.2** | Writes & Lookups — add/edit tasks, get-by-ID ✅ |
| **v1.3** | Read Tools — SQL filtering, search, list/count |
| **v1.4** | Output & UI — perspectives, TaskPaper, field selection |
| **v1.5** | Production Hardening — retry, crash recovery, fuzzy search |

---

## 🔗 Links

- 📖 [Full Documentation](https://hellothisisflo.github.io/omnifocus-operator) — features, architecture, examples
- 🐛 [Issues](https://github.com/HelloThisIsFlo/omnifocus-operator/issues)
- 💬 [Discussions](https://github.com/HelloThisIsFlo/omnifocus-operator/discussions)

---

## 📄 License

MIT

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. In short: fork, branch, test, PR.
