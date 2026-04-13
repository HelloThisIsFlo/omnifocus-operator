# TaskPaper Format Specification

**Document Status:** Comprehensive research-based specification (2026-02-21)
**Sources:** Official TaskPaper documentation, OmniFocus Automation documentation, community conventions, and format analysis

---

## Overview

TaskPaper is a plain text to-do list format created and maintained by Jesse Grosjean at Hog Bay Software (since 2006). The format is designed to be:
- **Human-readable:** Plain text files editable in any text editor
- **Machine-parseable:** Consistent syntax for projects, tasks, notes, and tags
- **Hierarchical:** Uses indentation to represent nesting relationships
- **Flexible:** Supports custom tags with optional values for extensibility

The format remains a living standard, with TaskPaper 3 (the current version) providing a modernized implementation while maintaining backward compatibility with the original plain text foundation.

---

## Basic Syntax

### Item Types

TaskPaper defines three item types, identified by their line prefix or suffix:

#### 1. Projects
**Syntax:** Line ending with a colon `:`

```
Project Name:
  Subtask project:
```

- Projects typically serve as container items for grouping related tasks
- Marked by trailing colon (`:`) at the end of the line
- Can be nested via indentation
- May contain tasks, notes, and other projects as children
- In many TaskPaper implementations, projects can have tags just like tasks

#### 2. Tasks
**Syntax:** Line starting with hyphen-space `- `

```
- Task name
  - Nested task
```

- Marked by `- ` (hyphen followed by space) at the start of the line
- Can be nested via indentation under projects or other tasks
- Are leaf items by default (can contain notes but not other tasks in basic format)
- Can have tags appended to the same line
- Completion status may be tracked via `@done` tag

#### 3. Notes
**Syntax:** Plain line (not starting with `- ` and not ending with `:`)

```
This is a note
  This is an indented note
```

- Any line that doesn't start with `- ` and doesn't end with `:` is a note
- Can appear at any indentation level
- Typically used for documentation, descriptions, or metadata
- In some implementations, notes inherit tags from their parent task (when used for task descriptions)

### Indentation & Hierarchy

**Indentation rule:** Use tabs or consistent spaces (typically 2 or 4 spaces) to indicate nesting.

```
Project:
  - Task 1
  - Task 2
    Subtask note
  - Task 3
    Subtask Project:
      - Subtask task
```

Important notes:
- Indentation is relative to the parent item
- Child items must be indented relative to their parent
- Mixed indentation (tabs vs spaces) may cause parsing issues — consistency is critical
- Depth is determined purely by indentation level
- The parser does not require a specific indentation width, but consistency within a file is essential

---

## Tags

Tags are the primary mechanism for attaching metadata to items. They follow the format `@tagname` or `@tagname(value)`.

### Syntax

**Basic tag:** `@tagname`
```
- Buy milk @shopping
```

**Tagged with value:** `@tagname(value)`
```
- Buy milk @due(2026-02-28)
- Deploy to production @estimate(120)
```

**Multiple tags on one line:**
```
- Review proposal @due(2026-02-25) @context(home) @flagged
```

### Tag Parsing Rules

1. **Detection:** Tags begin with `@` and continue until whitespace or end-of-line
2. **Value syntax:** Tags with values use parentheses: `@tagname(value)`
3. **Special characters in values:** Values can contain spaces, dates, numbers, and punctuation
   - Date formats are typically ISO8601 (YYYY-MM-DD) but the tag value itself is just a string
   - Values with spaces should be handled by the parser
4. **Case sensitivity:** Tag names are typically case-sensitive in parsers
5. **Tag position:** Tags can appear anywhere in the line, typically at the end, but some parsers may support them mid-text
6. **Escaped characters:** If a value contains parentheses, they should generally not appear or should be escaped (format varies by implementation)

### Standard Tags (TaskPaper Conventions)

The following tags are conventionally used across TaskPaper-compatible systems:

| Tag | Format | Meaning | Notes |
|-----|--------|---------|-------|
| `@done` | `@done` or `@done(date)` | Task completed | Typically marks a task as finished. Some systems use `@done(YYYY-MM-DD)` to record completion date |
| `@dropped` | `@dropped` or `@dropped(date)` | Task dropped/cancelled | Task will not be completed. Optional date for when it was dropped |
| `@flagged` | `@flagged` | Task is flagged for priority | No value parameter; binary presence/absence |
| `@due` | `@due(date)` | Task due date | Date in format YYYY-MM-DD (ISO8601) |
| `@defer` | `@defer(date)` | Defer until date | Task should not appear in "available" lists until this date. Format: YYYY-MM-DD |
| `@context` | `@context(name)` | Context/location/people | Common GTD (Getting Things Done) tag for grouping by context |
| `@estimate` | `@estimate(minutes)` | Time estimate | Duration in minutes (integer) |
| `@parallel` | `@parallel` | Run in parallel | Indicates tasks under this project can run simultaneously (project-level) |
| `@sequential` | `@sequential` | Run sequentially | Indicates tasks under this project must be completed in order (project-level) |
| `@autodone` | `@autodone` | Auto-complete when children done | Typically used on projects: when all subtasks are done, parent auto-completes |

### Less Common Tags (Extended Conventions)

| Tag | Format | Notes |
|-----|--------|-------|
| `@repeat` | `@repeat(rule)` | Recurring task (format varies by implementation) |
| `@repeat-method` | `@repeat-method(value)` | How recurrence is calculated (e.g., "fixed", "due", "completion") |
| `@repeat-rule` | `@repeat-rule(rrule)` | RFC5545 recurrence rule format |
| `@tags` | `@tags(comma,separated,list)` | Tag assignment to items (some systems use this for categorization) |

---

## OmniFocus-Specific TaskPaper Conventions

OmniFocus is a task management application for macOS and iOS that supports TaskPaper format for both import and export. The following is based on OmniFocus's interpretation and extension of the TaskPaper format.

### OmniFocus Export Format

When OmniFocus exports to "plain text" or TaskPaper format, it produces:

1. **Projects as items ending with `:`**
   ```
   Personal:
   ```

2. **Tasks as items starting with `- `**
   ```
   - Complete quarterly review
   ```

3. **Nesting via indentation**
   ```
   Work:
     - Project A:
       - Task 1
       - Task 2
     - Task 3
   ```

4. **Action groups** (hierarchical task collections) are represented as projects (ending with `:`)
   ```
   Review Meeting Prep:
     - Gather documents
     - Create slides
     - Practice presentation
   ```

### OmniFocus-Recognized Tags on Import

OmniFocus recognizes and properly imports the following tags from TaskPaper format:

| Tag | Format | OmniFocus Behavior |
|-----|--------|-------------------|
| `@due` | `@due(YYYY-MM-DD)` | Sets the task due date. Time component often ignored in import |
| `@defer` | `@defer(YYYY-MM-DD)` | Sets the task defer/start date (not available date in all versions) |
| `@flagged` | `@flagged` | Marks task as flagged for priority visibility |
| `@done` | `@done` or `@done(YYYY-MM-DD)` | Marks task as completed. Date may be stored but not always displayed |
| `@parallel` | `@parallel` | On projects: allows child tasks to be worked on simultaneously |
| `@sequential` | `@sequential` | On projects: enforces strict task ordering (one task at a time) |
| `@autodone` | `@autodone` | On projects: automatically marks project complete when all children complete |
| `@estimate` | `@estimate(minutes)` | Sets the estimated duration for time tracking |
| `@context` | `@context(name)` | Creates or applies an OmniFocus context tag |
| `@dropped` | `@dropped` or `@dropped(YYYY-MM-DD)` | Marks task as dropped/abandoned |

### OmniFocus Export Conventions

When OmniFocus exports to TaskPaper format:

1. **Due dates** are included as `@due(YYYY-MM-DD)`
2. **Defer dates** are included as `@defer(YYYY-MM-DD)` when present
3. **Completed tasks** are marked with `@done` (may include completion date depending on version)
4. **Flagged tasks** include `@flagged` tag
5. **Estimated duration** is included as `@estimate(minutes)` when set
6. **Context tags** are exported as `@context(context_name)`
7. **Project settings** like sequential/parallel are exported as `@sequential` or `@parallel` on the project line
8. **Project autodone** behavior is exported as `@autodone` when enabled

### OmniFocus Folder Structure

OmniFocus folders are represented in TaskPaper export as plain hierarchy. Folders are NOT indicated by a special syntax — they appear as nested projects:

```
Folder A:
  Project 1:
    - Task 1
    - Task 2
  Project 2:
    - Task 3
```

On import, TaskPaper does not preserve folder assignments. Instead:
- Top-level projects may map to OmniFocus folders (depending on import configuration)
- Nested projects structure is preserved
- Folder assignments must be manually set in OmniFocus after import, OR
- A convention (like prefixing project names) can be used to indicate folder assignment

### Nesting in OmniFocus Export

OmniFocus exports full hierarchy:
- Folders contain projects
- Projects contain action groups (represented as sub-projects, ending with `:`)
- Action groups and projects contain tasks (starting with `- `)
- Tasks can contain notes (plain lines)

Example:
```
Work:
  Project Alpha:
    - Subtask 1
    - Subtask 2
    Subtask 1 notes here
  Project Beta:
    Phase 1:
      - Task A
      - Task B
    Phase 2:
      - Task C
```

---

## Format Examples

### Basic Structure
```
Inbox:
  - Buy groceries @due(2026-02-28)
  - Email Sarah about meeting @defer(2026-02-24)

Personal Projects:
  Home Renovation:
    - Get quotes from contractors @estimate(120)
    - Decide on color scheme
      Need to gather paint samples first
    - Schedule inspection @due(2026-03-15)

  Fitness:
    - Monday: Running @context(morning)
    - Tuesday: Weight training @context(gym)

Work:
  Quarterly Review:
    - Compile performance data @due(2026-02-28) @estimate(180)
    - Write self-assessment @due(2026-03-01)
    - Schedule meeting with manager @context(work)

  Project X @sequential @due(2026-03-31):
    - Phase 1: Research @done(2026-02-15)
    - Phase 2: Design @estimate(400)
    - Phase 3: Implementation @estimate(800)
    - Phase 4: Testing @estimate(200)
```

### Tag Examples

```
- Buy milk @shopping @flagged @due(2026-02-22)
- Review proposal @context(office) @estimate(60) @due(2026-02-25)
- Call dentist @context(phone) @defer(2026-02-23)
- Completed project @done(2026-02-20) @estimate(480)
- Archived feature request @dropped(2026-02-10)
```

### Hierarchical Structure

```
Company Organization:
  Engineering:
    Backend Team:
      - Code review for PR #123 @estimate(90)
      - Fix database performance @estimate(480) @due(2026-03-01)
      - Infrastructure upgrade @sequential:
        - Audit current setup @done
        - Plan migration
        - Execute migration
        - Validate
    Frontend Team:
      - Design system overhaul @parallel:
        - Button component
        - Input components
        - Modal component
```

---

## Limitations & What Cannot Be Represented

The following OmniFocus concepts cannot be directly represented in TaskPaper format:

### 1. Review Intervals
OmniFocus projects have "review" functionality with review intervals (e.g., "review every 2 weeks"). TaskPaper has no syntax for this.
- **Workaround:** Custom tag like `@review-interval(2 weeks)` (non-standard)

### 2. Complex Recurrence Rules
While `@repeat-rule(rrule)` can capture some RFC5545 recurrence, not all OmniFocus recurrence patterns map cleanly.
- **Workaround:** Document the recurrence rule as a tag value or note

### 3. Effective (Inherited) Dates
OmniFocus computes effective due dates when a task inherits a due date from its parent project. TaskPaper does not have syntax for explicitly marking computed values.
- **Workaround:** On export, OmniFocus includes the computed effective date on the task itself. On re-import, these become explicit dates (losing the inheritance relationship).

### 4. Task Status Computed Property
OmniFocus computes task status (`Available`, `Overdue`, `Next`, `Blocked`, `DueSoon`) from multiple fields (due date, defer date, sequential project position, completion status). TaskPaper has no syntax for this.
- **Workaround:** Status is re-computed by the application on import based on due/defer dates and sequential constraints.

### 5. Perspectives
OmniFocus has "perspectives" — saved filtered views. TaskPaper format includes no way to represent these.
- **Workaround:** Not applicable; perspectives are application-specific and must be recreated manually.

### 6. Task/Project IDs
OmniFocus maintains unique internal IDs for each task and project. TaskPaper format has no syntax for storing these.
- **Workaround:** IDs must be regenerated on import; there is no stable identifier mapping.

### 7. Task Assignment & Collaboration
OmniFocus (iOS/Mac) supports assignment to people. TaskPaper has no standard syntax for this.
- **Workaround:** Use `@assigned(name)` as a custom convention

### 8. Attachments & File References
OmniFocus supports file attachments and rich note content. TaskPaper is plain text only.
- **Workaround:** Store file paths in notes; linking is manual

### 9. Subtask Constraints in Pure Format
While TaskPaper can represent parent-child relationships through indentation, some OmniFocus subtask features (like "subtasks block parent until complete") don't have syntax equivalents.
- **Workaround:** Use `@sequential` on projects as a proxy

### 10. Custom Metadata Beyond Tags
OmniFocus stores various metadata (creation date, modification date, completion date for computed status, etc.). TaskPaper supports only tags and line content.
- **Workaround:** Encode metadata in tag values (e.g., `@created(2026-02-01)`, `@modified(2026-02-20)`)

---

## Parsing Considerations

### Whitespace Handling
- **Leading whitespace:** Defines hierarchy level. Preserve exactly.
- **Trailing whitespace:** May be significant (some parsers preserve, others trim). Best practice: trim trailing whitespace in exported files.
- **Blank lines:** Typically treated as separators; they don't create items. Some parsers preserve them for readability, others ignore them.

### Line Endings
- **Unix (LF):** `\n` — standard
- **Windows (CRLF):** `\r\n` — supported by most modern parsers
- **Classic Mac (CR):** `\r` — rarely used in modern systems

### Character Encoding
- **UTF-8:** Standard and recommended
- **ASCII:** Subset of UTF-8; supported but limits internationalization
- **BOM (Byte Order Mark):** May cause parsing issues; should be avoided

### Edge Cases
1. **Colon in project names:** A line like `Project: The Sequel:` will be parsed as a project called `Project: The Sequel`
2. **Hyphen in task names:** A line like `- - Items to buy` is a task named `- Items to buy` (hyphen after the separator is not special)
3. **At-sign in notes:** An `@` symbol in a plain note line (not starting with `- `) is NOT treated as a tag start — only in task/project lines
4. **Tag values with parentheses:** The parser reads until the closing `)`. Nested parentheses are not supported.

---

## Import/Export Semantics

### Import Behavior (TaskPaper → OmniFocus)

When OmniFocus imports a TaskPaper file:

1. **Projects** (lines ending with `:`) become OmniFocus projects or action groups
2. **Tasks** (lines starting with `- `) become OmniFocus tasks
3. **Notes** (plain lines) become notes attached to their parent task
4. **Indentation hierarchy** is preserved
5. **Tags are processed:** Recognized tags (like `@due`, `@defer`, `@flagged`) are converted to OmniFocus properties
6. **Unknown tags** are preserved as text within task names or notes (depending on implementation)
7. **Folder assignments:** Not inferred from TaskPaper structure; must be set manually or via scripting

### Export Behavior (OmniFocus → TaskPaper)

When OmniFocus exports to TaskPaper:

1. **All projects** are exported as lines ending with `:`
2. **All tasks** are exported as lines starting with `- `
3. **All notes** are exported as plain lines (indented under their parent)
4. **Dates** are converted to ISO8601 format (`YYYY-MM-DD`)
5. **Properties become tags:** due dates → `@due(...)`, flags → `@flagged`, estimates → `@estimate(...)`
6. **Completion status** is marked with `@done` (with optional date)
7. **Folder information** is NOT explicitly exported (you see nested project hierarchy but not folder names)

---

## Conformance to Official TaskPaper Spec

This specification is based on:
- **Official TaskPaper documentation** from Hog Bay Software / Jesse Grosjean
- **OmniFocus automation documentation** (omni-automation.com)
- **Community conventions** documented in forums, blogs, and open-source TaskPaper parsers
- **Practical usage patterns** from TaskPaper 3 (the current stable version)

**Gaps and Uncertainties:**
- The official TaskPaper reference has limited public online documentation; much of the spec is inferred from the application itself and community usage
- OmniFocus's exact export behavior varies slightly between versions (3 vs 4 iOS, macOS versions), and not all variants have been tested here
- Custom extensions (like `@repeat-rule` or proprietary tags) are conventions, not official spec

---

## Recommendations for OmniFocus Operator Implementation

For the OmniFocus Operator MCP server, consider:

1. **Import from TaskPaper:**
   - Parse projects (ending with `:`) and tasks (starting with `- `)
   - Build hierarchy from indentation
   - Extract all `@tagname(value)` patterns
   - Map OmniFocus-recognized tags to task properties
   - Handle unknown tags gracefully (store as custom tags or in notes)

2. **Export to TaskPaper:**
   - Output projects with trailing `:`
   - Output tasks with `- ` prefix
   - Include all task properties as tags (`@due`, `@defer`, `@flagged`, `@estimate`, etc.)
   - Preserve folder structure as nested projects (but document that folder mapping is lost on re-import)
   - Use ISO8601 dates (`YYYY-MM-DD`)

3. **Caveats:**
   - Review intervals, perspectives, and computed effective dates cannot round-trip through TaskPaper
   - Task IDs are not preserved
   - Attachments and rich media are not supported
   - Full fidelity requires storing data outside TaskPaper (e.g., in a JSON sidecar or database)

---

## References

- **TaskPaper Official:** www.taskpaper.com
- **OmniFocus Automation:** omni-automation.com/omnifocus
- **OmniFocus Support:** support.omnigroup.com
- **Community Forums:** forum.hogbaysoftware.com (TaskPaper), omnifocus-community resources
- **RFC5545:** iCalendar Recurrence Rule Specification (used for advanced recurrence)

---

## Document History

| Date | Version | Status |
|------|---------|--------|
| 2026-02-21 | 1.0 | Initial comprehensive specification based on research and project context |

