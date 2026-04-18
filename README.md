# 🎯 OmniFocus Operator

**The last OmniFocus MCP Server you'll ever need.**

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white)
![Tests 2086](https://img.shields.io/badge/tests-2086-brightgreen)
![Coverage 97%](https://img.shields.io/badge/coverage-97%25-brightgreen)
![macOS only](https://img.shields.io/badge/platform-macOS-lightgrey?logo=apple)

Production-grade MCP server exposing OmniFocus as structured task infrastructure for AI agents. Agent-first design, SQLite-cached performance, 2,086 tests.

### [**→ See the full landing page**](https://hellothisisflo.github.io/omnifocus-operator) — features, architecture, benchmarks, and comparison

---

## 🚀 Quick Start

**Prerequisites:** macOS, OmniFocus 4, Python 3.12+

**Claude Desktop config** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "omnifocus-operator": {
      "command": "uvx",
      "args": ["omnifocus-operator"]
    }
  }
}
```

That's it. No install step — `uvx` downloads, isolates, and runs the server automatically.

**Or just ask your agent:**

> Set up the OmniFocus Operator MCP server for me — uvx omnifocus-operator

<details>
<summary><strong>Development install (contributors)</strong></summary>

```bash
git clone https://github.com/HelloThisIsFlo/omnifocus-operator.git
cd omnifocus-operator
uv sync
```

See [CONTRIBUTING.md](https://github.com/HelloThisIsFlo/omnifocus-operator/blob/main/CONTRIBUTING.md) for dev workflow details.

</details>

---

## ✨ Features

- ⚡ **46ms reads** — SQLite caching gives 30–60x faster reads than bridge-only servers
- 🛠️ **11 MCP tools** — lookups, filtered lists, task creation & editing
- 🤖 **Agent-first design** — warnings that teach, errors that educate, guidance in every response
- 🧪 **2,086 tests, 97% coverage** — strict mypy, no corners cut
- 🛡️ **Graceful degradation** — server stays alive no matter what, always recoverable
- 🔄 **Automatic fallback** — SQLite → OmniJS bridge when needed

See the [full documentation](https://hellothisisflo.github.io/omnifocus-operator) for architecture details, examples, and deep dives.

---

## 🛠️ Available Tools

### Lookups

| Tool | Description |
|------|-------------|
| `get_all` | Full OmniFocus database as structured data (last-resort debugging) |
| `get_task` | Single task by ID — urgency, availability, dates, tags, parent, project |
| `get_project` | Single project by ID — status, review interval, next task |
| `get_tag` | Single tag by ID — availability, parent hierarchy |

### List & Filter

| Tool | Description |
|------|-------------|
| `list_tasks` | Filter by date, availability, flags, tags, project, search — with pagination and field selection |
| `list_projects` | Filter by status, folder, review schedule, flags |
| `list_tags` | List tags with parent hierarchy |
| `list_folders` | List folders with parent hierarchy |
| `list_perspectives` | List custom perspectives |

### Write

| Tool | Description |
|------|-------------|
| `add_tasks` | Create tasks with full field control — parent, tags, dates, flags, notes, repetition rules |
| `edit_tasks` | Patch semantics — update fields, move tasks, complete/drop, manage tags and repetition rules |

All read tools are idempotent. Write tools reference projects and tags by name or ID.

---

## 🔍 Tool Examples

**Filter tasks** (`list_tasks`):

```json
{
  "query": {
    "flagged": true,
    "due": "soon",
    "availability": "remaining",
    "include": ["notes"],
    "limit": 10
  }
}
```

**Create a task** (`add_tasks`):

```json
{
  "items": [{
    "name": "Review Q3 roadmap",
    "parent": {"project": {"name": "Work Projects"}},
    "tags": ["Planning"],
    "dueDate": "2026-03-15T17:00:00",
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
    "moveTo": {"ending": {"project": {"name": "Work Projects"}}}
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

## 🗺️ Roadmap

| Version | Focus |
|---------|-------|
| **v1.0** | Foundation — read tools, three-layer arch, test suite ✅ |
| **v1.1** | Performance — SQLite caching, 30–60x speedup ✅ |
| **v1.2** | Writes & Lookups — add/edit tasks, get-by-ID ✅ |
| **v1.2.1** | Architectural Cleanup — contracts, service refactor, golden master tests ✅ |
| **v1.2.2** | FastMCP v3 Migration ✅ |
| **v1.2.3** | Repetition Rule Write Support ✅ |
| **v1.3** | Read Tools — SQL filtering, list/count, 5 new tools ✅ |
| **v1.3.1** | First-Class References — name resolution, `$inbox`, rich refs ✅ |
| **v1.3.2** | Date Filtering — 7 dimensions, shortcuts, calendar math ✅ |
| **v1.3.3** | Task Ordering — dotted notation, outline order ✅ |
| **v1.4** | Response Shaping & Batch Processing ✅ |
| **v1.4.1** | Task Properties & Subtree — presence flags, auto-complete, parallel/sequential, parent filter 🔧 |
| **v1.5** | UI & Perspectives — perspective switching, deep links |
| **v1.6** | Production Hardening — retry, crash recovery, serial execution |

---

## 🔗 Links

- 📖 [Full Documentation](https://hellothisisflo.github.io/omnifocus-operator) — features, architecture, examples
- 📦 [PyPI](https://pypi.org/project/omnifocus-operator/) — package page
- 🐛 [Issues](https://github.com/HelloThisIsFlo/omnifocus-operator/issues)
- 💬 [Discussions](https://github.com/HelloThisIsFlo/omnifocus-operator/discussions)

---

## 📄 License

Proprietary — all rights reserved. Free to use, not to redistribute. License under review.

## 🤝 Contributing

See [CONTRIBUTING.md](https://github.com/HelloThisIsFlo/omnifocus-operator/blob/main/CONTRIBUTING.md) for guidelines. In short: fork, branch, test, PR.
