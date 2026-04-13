# Python TaskPaper Library Evaluation

**Date:** 2026-02-21
**Context:** Evaluating options for parsing and serializing TaskPaper format files for the OmniFocus Operator MCP server.

---

## Executive Summary

The TaskPaper format is deliberately minimal—just indented text with `@tag(value)` syntax. While three published Python libraries exist, **all are essentially abandoned** (last commits 2011–2016), and all have Python 2 heritage or incomplete feature coverage.

**Recommendation:** Write a custom parser/serializer. It will be:
- Smaller, faster, and more maintainable than any dependency
- Tailored exactly to OmniFocus TaskPaper dialect
- Trivial to test and modify
- Zero external dependencies
- Production-ready in a few hours

---

## Library Evaluations

### 1. **python-taskpaper** (mattd/python-taskpaper)

**Repository:** https://github.com/mattd/python-taskpaper
**PyPI:** https://pypi.org/project/python-taskpaper/

#### Maintenance Status
- **Last Commit:** March 17, 2011 (15 years ago)
- **Stars:** 30
- **Forks:** 12
- **Contributors:** 2
- **Open Issues/PRs:** None visible
- **Status:** Essentially dormant

#### Python Compatibility
- **Declared:** Python 2.7 or 3.3+
- **Actual Compatibility:** Python 3.10+ untested; code uses Python 2 idioms (`xrange`, `types.StringTypes`)
- **Assessment:** Code may work but not validated on modern Python

#### API & Features

**Core Classes:**
- `TaskPaper`: Container for parsing/managing documents
- `TaskItem`: Individual entries with tag and hierarchy support

**Supported Operations:**
- ✅ Parse multi-line documents with indentation-based hierarchy
- ✅ Extract and manage tags (`@tag` and `@tag(value)`)
- ✅ Parent-child relationship tracking
- ✅ Add/remove tags dynamically
- ✅ Serialize back to TaskPaper format
- ✅ Filter by tags using bracket notation
- ✅ Classify items (task, project, note)

**Code Quality:**
- Basic but functional design
- Uses Python dunder methods for natural iteration (`__iter__`, `__str__`, `__getitem__`)
- Some defensive practices (assertions, null checks)
- Limited error handling for malformed input
- Python 2 syntax idioms present

#### Serialization Support
- ✅ Writes TaskPaper format
- Uses `__str__()` to reconstruct indented output
- Proper indentation reconstruction

#### Dependencies
- None specified (uses standard library)

#### License
- GPL-3.0 (requires source disclosure if distributed)

#### Assessment
**Score: 4/10**
- Covers core features but abandoned for 15 years
- Python 2 heritage makes Python 3.10+ uncertain
- No recent maintenance or bug fixes
- GPL license may restrict certain uses
- Not recommended for production

---

### 2. **TodoFlow** (bevesce/TodoFlow)

**Repository:** https://github.com/bevesce/TodoFlow

#### Maintenance Status
- **Last Commit:** ~2016 (10 years ago)
- **Latest Release:** 5.0.0 (October 8, 2016)
- **Contributors:** Active maintainer ~2010–2016, then abandoned
- **Open Issues:** None
- **Status:** Dormant; removed file I/O in v5.0.0

#### Python Compatibility
- **Declared:** Not explicitly specified
- **Codebase:** 99.9% Python
- **Python 3.10+ Support:** Untested; likely OK but unverified

#### API & Features

**Core Classes:**
- `Todos`: Main container for parsing and managing documents
- `Todoitem`: Individual task/project/note entries

**Supported Operations:**
- ✅ Parse plain text to-do lists in TaskPaper syntax
- ✅ Filter and search (including TaskPaper 3 query syntax support)
- ✅ Tag management system
- ✅ Support for projects, tasks, and notes
- ✅ Stringify todos for file storage

**Notable Limitation:**
- **v5.0.0 removed dedicated file I/O methods** — users must handle file reading/writing independently
- Must create todos from strings and stringify for storage

**Code Quality:**
- Well-documented for its era (2010–2016)
- Clean separation of concerns
- Query syntax support is a plus
- Advanced feature set

#### Serialization Support
- ✅ Can stringify (convert back to TaskPaper format)
- File I/O deliberately removed; users handle this

#### Dependencies
- Not clearly specified

#### License
- Not visible in search results; check GitHub directly

#### Assessment
**Score: 3/10**
- Good feature set but abandoned 10 years ago
- File I/O removal is odd and inconvenient
- Query syntax is nice but not essential for MCP
- Python 3.10+ compatibility untested
- Not recommended for production

---

### 3. **RobTrew/tree-tools Python Parser**

**Repository:** https://github.com/RobTrew/tree-tools
**Specific File:** `TaskPaper scripts/Python parser for TaskPaper and FoldingText.md`

#### Distribution & Status
- **Not Published to PyPI** — available as standalone Python file in repo
- **Part of:** Larger tree-tools utility collection
- **Last Repo Activity:** Unknown; repo appears to have mixed-age content
- **Status:** Appears maintained as part of larger project

#### Python Compatibility
- **Declared:** Not explicitly specified
- **Style:** Appears to be Python 3 compatible
- **Assessment:** Likely works on Python 3.10+

#### API & Features

**Available Versions:**
- `ft_tp_parse_022.py` — Full parser (TaskPaper + FoldingText)
- `tp_light_parse_022.py` — TaskPaper-only, lightweight

**Core Functions:**
- `is_tp(str_text)` — Format detection (TaskPaper vs FoldingText)
- `get_ft_tp_parse(str_text, bln_is_tp)` — Parse either format

**Output Format:**
- Returns list of dictionaries (one per line)
- Dictionary keys: `id`, `parentID`, `text`, `line`, `lineNumber`, `nestedLevel`, `tagNames`, `tags`, `type`, `typeIndentLevel`, `childIndex`, etc.
- Virtual root node (id=0) for document structure

**Supported Elements:**
- ✅ Node types (project, task, note)
- ✅ Hierarchical nesting
- ✅ Parent-child relationships
- ✅ Tags in `@key(value)` format
- ✅ Document outline structure
- ❌ Inline Markdown formatting (intentionally left unparsed)
- ❌ Query language (not provided)

**Serialization Support:**
- ❌ No documented write capability — parse-only

#### Code Quality
- Described as "provisional draft"
- Straightforward algorithmic approach
- No advanced features
- No error handling documentation

#### Dependencies
- Standard library only

#### License
- Not clearly stated; check GitHub directly

#### Assessment
**Score: 5/10**
- Better Python 3 compatibility than alternatives
- Good reference implementation
- **No write/serialize support** — parse-only
- Not suitable for read-write MCP server
- More of a reference implementation than production library

---

## Format Complexity Analysis

### What Is TaskPaper Format?

TaskPaper is **deliberately minimal**. Per the [OmniFocus TaskPaper Reference](https://support.omnigroup.com/omnifocus-taskpaper-reference/) and [TaskPaper User's Guide](https://guide.taskpaper.com/getting-started/):

**Core Elements:**
- **Projects:** Lines ending with `:` (e.g., `Groceries:`)
- **Tasks:** Lines starting with `- ` (e.g., `- Milk`)
- **Notes:** Any other unformatted text
- **Tags:** `@tagname` or `@tagname(value)` or `@tagname(value1,value2)`
- **Indentation:** Tabs define hierarchy (not spaces)

**Supported by OmniFocus:**
```
@due(date)               – Due date
@defer(date)             – Start date
@done(date)              – Completion date (marks done)
@estimate(duration)      – Time estimate
@flagged                 – Flagged status
@tags(name1,name2)       – OmniFocus tags
@parallel(bool)          – Parallel vs sequential
@autodone(bool)          – Auto-complete children
@repeat-rule             – RFC2445 ICS recurrence
@repeat-method           – Repeat type (fixed, from-completion, etc.)
```

**Parsing Requirements:**
1. Read lines with proper indentation tracking (tabs only)
2. Detect item type (project/task/note) from line prefix/suffix
3. Extract tags from line (can appear anywhere, not just at end)
4. Parse tag values (including comma-separated lists)
5. Reconstruct parent-child hierarchy from indentation
6. Preserve exact formatting when round-tripping

**Complexity Assessment:**
- **Is it complex?** No. It's a simple indented text format.
- **Are existing libraries good?** No. The ecosystem is abandoned.
- **Is custom parsing justified?** Yes. A custom parser is simpler, faster, and better than any published library.

---

## Comparison Table

| Aspect | python-taskpaper | TodoFlow | RobTrew Parser | Custom Parser |
|--------|------------------|----------|----------------|---------------|
| **Last Commit** | 2011 (15y) | 2016 (10y) | Unknown | N/A |
| **Python 3.10+** | ? Untested | ? Untested | ✅ Likely | ✅ Fresh |
| **Parse Accuracy** | ✅ Good | ✅ Good | ✅ Good | ✅ Best |
| **Write Support** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |
| **API Quality** | ⚠️ Basic | ⚠️ Good | ⚠️ Basic | ✅ Custom |
| **Dependencies** | ✅ None | ? Unknown | ✅ None | ✅ None |
| **Maintenance** | ❌ None | ❌ None | ? Unknown | N/A |
| **License** | GPL-3.0 | ? | ? | Custom |
| **PyPI Published** | ✅ Yes | ❌ No | ❌ No | N/A |
| **Lines of Code** | ~500 | ~500+ | ~300 | ~200–400 |
| **Recommended** | ❌ No | ❌ No | ❌ No | ✅ Yes |

---

## Recommendation: Build a Custom Parser

### Why Build Custom?

1. **Simplicity:** TaskPaper format is trivial. A robust parser is ~200–400 lines.
2. **No Maintenance Burden:** All published libraries are abandoned.
3. **Perfect Control:** Tailored to OmniFocus dialect, not a generic solution.
4. **Zero Dependencies:** Faster startup, simpler deployment, no version conflicts.
5. **Better Testing:** You control the test suite; validated against Flo's actual OmniFocus output.
6. **Better Performance:** No object overhead from library abstractions.
7. **Extensibility:** Easy to add OmniFocus-specific features later.

### Implementation Approach

A custom parser would:
1. Read lines, tracking indentation stack
2. Classify each line (project/task/note) from prefix/suffix
3. Extract `@tag(value)` patterns using regex
4. Build tree of `TaskItem` objects with parent pointers
5. Serialize back by walking tree and outputting indented lines

**Estimated effort:** 3–5 hours for a production-ready implementation with tests.

**Benefits:**
- Clear, readable code
- Comprehensive test coverage (round-trip parsing)
- Handles edge cases specific to OmniFocus
- Documented and maintainable by future developers
- No dependency management

---

## Conclusion

**Do not use any of the published libraries.**

- `python-taskpaper`: Abandoned since 2011, Python 2 legacy, GPL-licensed
- `TodoFlow`: Abandoned since 2016, incomplete features, removed file I/O
- `RobTrew Parser`: Parse-only, no write support, not published as library

**Build a custom parser.** The TaskPaper format is simple enough that a bespoke solution is the right engineering choice. It will be cleaner, faster, and more maintainable than depending on abandoned code.

---

## References

- [OmniFocus TaskPaper Reference Guide](https://support.omnigroup.com/omnifocus-taskpaper-reference/)
- [TaskPaper User's Guide](https://guide.taskpaper.com/getting-started/)
- [python-taskpaper on PyPI](https://pypi.org/project/python-taskpaper/)
- [python-taskpaper GitHub](https://github.com/mattd/python-taskpaper)
- [TodoFlow GitHub](https://github.com/bevesce/TodoFlow)
- [RobTrew/tree-tools GitHub](https://github.com/RobTrew/tree-tools)
