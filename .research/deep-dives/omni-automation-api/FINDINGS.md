# Omni Automation (OmniJS) API for OmniFocus -- Research Findings

> Research into the Omni Automation JavaScript runtime built into OmniFocus.
> This is NOT JXA (JavaScript for Automation / osascript). It is Omni Group's
> own JavaScript plugin/automation runtime embedded in OmniFocus itself.

**Research date:** 2026-03-04

---

## Executive Summary

Omni Automation is a JavaScript runtime embedded directly in OmniFocus (and other Omni apps). It uses **direct property access** (no parentheses), has the **Database as its implicit `this`** context, and provides a rich object model for tasks, projects, tags, folders, and perspectives. The `operatorBridgeScript.js` in this project already uses this runtime correctly.

### JXA vs Omni Automation -- Key Differences

| Aspect | JXA (`osascript -l JavaScript`) | Omni Automation (OmniJS) |
|---|---|---|
| Runtime | macOS system scripting bridge | Omni's embedded JS engine |
| Entry point | `Application("OmniFocus")` | Implicit `Database` as `this` |
| Property access | Methods with `()`: `p.name()` | Direct properties: `p.name` |
| Root task | `p.task()` | `p.task` |
| Flattened collections | `doc.flattenedProjects()` | `flattenedProjects` (global) |
| Status enums | Not directly available | `Task.Status.Available`, etc. |
| Cross-bridge | N/A | `evaluateJavascript()` from JXA |
| Script argument | N/A | `argument` variable (URL scheme) |

**Important note on existing project code:**
- `operatorBridgeScript.js` -- uses **Omni Automation** style (correct: `p.name`, `t.tags.map(...)`)
- Audit scripts in `scripts/01-*.js` through `scripts/12-*.js` -- use **JXA** style (correct for JXA context: `p.name()`, `p.task()`)

---

## 1. How to Access Entities

### Implicit Database Context

In the Omni Automation console (and URL scheme scripts), the **Database** is the implicit top-level context (`this`). All Database properties are available as bare globals:

```javascript
// These are all Database properties accessible without any prefix:
flattenedTasks      // TaskArray -- ALL tasks in the database (flat)
flattenedProjects   // ProjectArray -- ALL projects (flat)
flattenedTags       // TagArray -- ALL tags (flat)
flattenedFolders    // FolderArray -- ALL folders (flat)
flattenedSections   // SectionArray -- ALL folders + projects (flat)

inbox               // Inbox -- tasks in inbox
library             // Library -- top-level folders and projects
tags                // Tags -- top-level tags (hierarchical root)
folders             // FolderArray -- top-level folders only
projects            // ProjectArray -- top-level projects only
```

### Comparison: JXA vs Omni Automation

```javascript
// JXA (osascript -l JavaScript)
const app = Application("OmniFocus")
const doc = app.defaultDocument
const projects = doc.flattenedProjects()    // method call with ()
const name = projects[0].name()              // method call with ()

// Omni Automation (console / URL scheme / plugin)
const projects = flattenedProjects           // bare global, no ()
const name = projects[0].name                // direct property, no ()
```

### Named Lookup

```javascript
// Find by exact name (top-level only):
projectNamed("My Project")     // Project or null
folderNamed("My Folder")       // Folder or null
tagNamed("My Tag")             // Tag or null

// Find by name (flattened / anywhere in hierarchy):
flattenedProjects.byName("My Project")   // Project or null
flattenedTags.byName("My Tag")           // Tag or null
flattenedTasks.byName("Build Shed")      // Task or null

// Find by ID:
Project.byIdentifier("abc123")   // Project or null
Task.byIdentifier("abc123")      // Task or null
Tag.byIdentifier("abc123")       // Tag or null
Folder.byIdentifier("abc123")    // Folder or null

// Smart matching (fuzzy):
projectsMatching("keyword")   // ProjectArray
foldersMatching("keyword")    // FolderArray
tagsMatching("keyword")       // TagArray
```

### Flattened Array Methods

All flattened arrays (`TaskArray`, `ProjectArray`, `TagArray`, `FolderArray`) support:

```javascript
flattenedTasks.byName("name")   // first match by name, or null
flattenedTasks.byID("id")       // first match by ID, or null
flattenedTasks.filter(fn)       // standard JS filter
flattenedTasks.map(fn)          // standard JS map
flattenedTasks.forEach(fn)      // standard JS forEach
```

---

## 2. Property Access Style

**Direct property access** -- no parentheses. This is the fundamental difference from JXA.

```javascript
// Correct (Omni Automation):
task.name                    // String
task.note                    // String
task.completed               // Boolean (read-only)
task.dueDate                 // Date or null
task.flagged                 // Boolean
task.taskStatus              // Task.Status enum value
task.tags                    // TagArray (read-only)
task.children                // Array of Task (read-only)
task.parent                  // Task or null (read-only)
task.containingProject       // Project or null (read-only)
task.id.primaryKey           // String

// WRONG (this is JXA style):
task.name()                  // ERROR in Omni Automation
task.completed()             // ERROR in Omni Automation
```

### Setting Properties

```javascript
task.name = "New Name"
task.note = "Updated note"
task.dueDate = new Date("2026-04-01")
task.deferDate = null                      // clear the defer date
task.flagged = true
task.sequential = false
task.estimatedMinutes = 30
project.status = Project.Status.OnHold
```

---

## 3. Key Globals

### Always Available

| Global | Type | Role |
|---|---|---|
| `this` | Database | The implicit scripting context; all Database properties are globals |
| `document` | DatabaseDocument | The current OmniFocus document |
| `app` | Application | The OmniFocus application object |
| `console` | Console | Standard console logging (`console.log()`, `console.clear()`) |
| `inbox` | Inbox | Inbox tasks container |
| `library` | Library | Top-level folders and projects |
| `tags` | Tags | Top-level tags container |
| `flattenedTasks` | TaskArray | All tasks, flat |
| `flattenedProjects` | ProjectArray | All projects, flat |
| `flattenedTags` | TagArray | All tags, flat |
| `flattenedFolders` | FolderArray | All folders, flat |
| `flattenedSections` | SectionArray | All folders + projects, flat |
| `folders` | FolderArray | Top-level folders |
| `projects` | ProjectArray | Top-level projects |

### Class Constructors (Always Global)

| Class | Purpose |
|---|---|
| `Task` | Task entity + `Task.Status`, `Task.RepetitionRule`, etc. |
| `Project` | Project entity + `Project.Status`, `Project.ReviewInterval` |
| `Tag` | Tag entity + `Tag.Status` |
| `Folder` | Folder entity + `Folder.Status` |
| `Perspective` | `Perspective.BuiltIn`, `Perspective.Custom` |
| `Database` | The Database class (implicit context) |
| `DatabaseObject` | Base class for all entities |
| `Calendar` | Date calculation utilities |
| `Color` | Color values |
| `Form` | Interactive form building |
| `Alert` | User alerts/dialogs |
| `URL` | URL handling and fetch |
| `Email` | Email composition |
| `Pasteboard` | Clipboard access |
| `Timer` | Scheduled execution |
| `Settings` | Synced preferences (across devices) |
| `Preferences` | Local preferences (per device) |

### URL Scheme Scripts

In scripts triggered via `omnifocus://localhost/omnijs-run?script=...&arg=...`:
- `argument` -- the decoded `&arg=` parameter value (can be string, array, or object)
- All other globals above are available

### Application Object (`app`)

```javascript
app.name              // "OmniFocus"
app.platformName      // "macOS", "iOS", or "iPadOS"
app.userVersion       // Version object
app.buildVersion      // Version object
app.commandKeyDown    // Boolean (macOS only)
app.optionKeyDown     // Boolean (macOS only)
app.shiftKeyDown      // Boolean (macOS only)
app.controlKeyDown    // Boolean (macOS only)
```

### Document & Window

```javascript
document.windows[0]                      // current/front window
document.windows[0].perspective          // current perspective
document.windows[0].selection.tasks      // selected tasks
document.windows[0].selection.projects   // selected projects
document.windows[0].selection.folders    // selected folders
document.windows[0].selection.tags       // selected tags
document.windows[0].selection.allObjects // all selected items
```

---

## 4. Entity Relationships

### Project <-> Root Task

Every project has an invisible "root task" that is the project's backing entity.

```javascript
const p = flattenedProjects[0]
const rootTask = p.task          // Task -- the project's root task (read-only)

// The root task holds task-level metadata:
p.task.added                     // Date -- creation timestamp
p.task.modified                  // Date -- modification timestamp
p.task.active                    // Boolean
p.task.effectiveActive           // Boolean
p.task.taskStatus                // Task.Status enum

// Project proxies many properties from/to its root task:
p.name === p.task.name           // true -- proxied
p.dueDate === p.task.dueDate     // true -- proxied
p.flagged === p.task.flagged     // true -- proxied

// But some task fields are ONLY on the root task (not on project):
// - added, modified, active, effectiveActive
// These are undefined/null on `p.*` but defined on `p.task.*`
```

### Task Hierarchy

```javascript
task.children           // Array of Task -- direct child tasks
task.flattenedTasks     // TaskArray -- ALL descendant tasks (recursive)
task.parent             // Task or null -- parent task
task.hasChildren        // Boolean
task.containingProject  // Project or null -- the project this task belongs to
task.inInbox            // Boolean -- whether task is in inbox
task.project            // Project or null -- non-null ONLY if this task IS a project root
```

### Tag Relationships

```javascript
task.tags               // TagArray -- tags assigned to this task
tag.tasks               // TaskArray -- all tasks with this tag
tag.availableTasks      // TaskArray -- available tasks with this tag
tag.remainingTasks      // TaskArray -- incomplete tasks with this tag
tag.children            // TagArray -- child tags
tag.flattenedTags       // TagArray -- all descendant tags
tag.parent              // Tag or null -- parent tag
tag.projects            // ProjectArray -- projects with this tag
```

### Folder Containment

```javascript
folder.children          // Array -- child folders + projects (mixed)
folder.folders           // FolderArray -- child folders only
folder.projects          // ProjectArray -- child projects only
folder.flattenedFolders  // FolderArray -- all descendant folders
folder.flattenedProjects // ProjectArray -- all descendant projects
folder.parent            // Folder or null
folder.sections          // SectionArray -- folders + projects
project.parentFolder     // Folder or null
```

---

## 5. Enum Access

### Task.Status

```javascript
Task.Status.Available    // task is actionable
Task.Status.Blocked      // task is blocked (by sequential ordering or deferred)
Task.Status.Completed    // task is completed
Task.Status.Dropped      // task is dropped
Task.Status.DueSoon      // task is due soon
Task.Status.Next         // task is next action in sequential project
Task.Status.Overdue      // task is overdue
Task.Status.all          // Array of all Task.Status values

// Usage:
task.taskStatus === Task.Status.Available   // comparison
```

### Project.Status

```javascript
Project.Status.Active    // default, ongoing
Project.Status.Done      // completed
Project.Status.Dropped   // abandoned
Project.Status.OnHold    // paused
Project.Status.all       // Array of all Project.Status values

// Usage:
project.status                                // read
project.status = Project.Status.OnHold        // write
```

### Tag.Status

```javascript
Tag.Status.Active
Tag.Status.Dropped
Tag.Status.OnHold
Tag.Status.all
```

### Folder.Status

```javascript
Folder.Status.Active
Folder.Status.Dropped
Folder.Status.all
```

### Enum Opacity

Omni Automation enums are **opaque objects**. They cannot be converted to strings:

```javascript
String(Task.Status.Available)    // "[object Object]" -- NOT "Available"
Task.Status.Available.name       // undefined
Task.Status.Available.toString() // "[object Object]"
```

You must use identity comparison (`===`) against the enum constants. The bridge script does this with a chain of `if` statements:

```javascript
function ts(s) {
  if (s === Task.Status.Available) return "Available"
  if (s === Task.Status.Blocked) return "Blocked"
  // ... etc.
  return null
}
```

For `Project.Status` and `Tag.Status`, the bridge script uses `.name` property which
may work on some status types but should be verified empirically.

### ApplyResult (Iteration Control)

```javascript
ApplyResult.Stop           // halt iteration
ApplyResult.SkipChildren   // skip descendants of current item
ApplyResult.SkipPeers      // skip siblings of current item
ApplyResult.all            // Array of all values
```

---

## 6. Database Queries and Operations

### Filtering (Standard JavaScript)

```javascript
// Filter tasks
flattenedTasks.filter(t => t.taskStatus === Task.Status.Available)
flattenedTasks.filter(t => t.flagged && !t.completed)
flattenedTasks.filter(t => t.dueDate && t.dueDate < new Date())

// Filter projects
flattenedProjects.filter(p => p.status === Project.Status.Active)

// Filter tags
flattenedTags.filter(tag => tag.remainingTasks.length > 0)
```

### The `apply()` Method (Recursive Traversal)

`apply()` recursively traverses hierarchies. Available on: `inbox`, `library`, `tags`, and instances of `Folder`, `Tag`, `Task`.

```javascript
// Traverse entire library hierarchy
library.apply(item => {
  if (item instanceof Project) {
    console.log("Project: " + item.name)
  }
  // return ApplyResult.Stop to halt
  // return ApplyResult.SkipChildren to skip subtree
})

// Traverse all tasks in a project
project.task.apply(task => {
  console.log(task.name)
})

// Search with early termination
var found = null
library.apply(item => {
  if (item instanceof Project && item.name === "Target") {
    found = item
    return ApplyResult.Stop
  }
})

// Traverse tag hierarchy
tags.apply(tag => {
  console.log(tag.name)
})
```

**`apply()` vs `forEach()`**: `forEach()` iterates only top-level items in a flat array. `apply()` recurses the entire hierarchy and supports early termination via `ApplyResult`.

### Database.Fetch

`Database.Fetch` is referenced in the API as a CallbackObject but is not documented with usage examples. The standard approach for querying is using `flattenedTasks` / `flattenedProjects` / etc. with `.filter()`. There is no documented "query language" or structured fetch API.

### Database Modification Methods

```javascript
// Move/duplicate
moveTasks(tasks, project)                    // move tasks to project
duplicateTasks(tasks, project)               // copy tasks to project
moveTags(tags, parentTag)                    // reorganize tags
moveSections(sections, folder)               // move projects/folders

// Delete
deleteObject(entity)                         // delete any database object

// Persistence
save()                                       // save to disk (implicit this = Database)
cleanUp()                                    // process inbox, remove empty items

// Undo
undo()                                       // undo last action
redo()                                       // redo last undone action
canUndo                                      // Boolean
canRedo                                      // Boolean

// URL resolution
objectForURL(url)                            // get DatabaseObject from omnifocus:// URL
```

---

## 7. `library.apply()` Pattern

The `library` property represents all top-level folders and projects. `library.apply()` recursively walks the entire project/folder hierarchy (but NOT tasks within projects -- only the structural containment of folders and projects).

```javascript
// Walk entire library structure
library.apply(item => {
  if (item instanceof Project) {
    // item is a Project
  } else if (item instanceof Folder) {
    // item is a Folder
  }
})
```

To walk tasks within a project, use `project.task.apply(...)`.

---

## 8. Entity Creation

### Creating Tasks

```javascript
// Basic (added to inbox by default)
new Task("Task Name")

// In a specific project
new Task("Task Name", project)

// At a specific position
new Task("First task", project.beginning)
new Task("Last task", project.ending)
new Task("Before X", someTask.before)
new Task("After X", someTask.after)

// In inbox at specific position
new Task("First", inbox.beginning)
new Task("Last", inbox.ending)

// From transport text (shorthand syntax)
Task.byParsingTransportText("Buy groceries @Errands #today ! $15m :: Shopping //Remember: organic")
// Supports: @ (tag), # (date), ! (flag), $ (estimate), :: (project), // (note)
```

### Creating Projects

```javascript
new Project("Project Name")
new Project("Project Name", folder)
new Project("Project Name", folder.ending)
```

### Creating Tags

```javascript
new Tag("Tag Name")
new Tag("Child Tag", parentTag)
new Tag("Child Tag", parentTag.beginning)

// Find-or-create pattern
tag = tagNamed("Work") || new Tag("Work")
tag = flattenedTags.byName("Work") || new Tag("Work")
```

### Creating Folders

```javascript
new Folder("Folder Name")
new Folder("Folder Name", library.beginning)
new Folder("Nested", parentFolder.ending)
```

---

## 9. Entity Modification

### Task Properties

```javascript
task.name = "Updated Name"
task.note = "New note content"
task.dueDate = new Date("2026-06-15")
task.deferDate = new Date("2026-06-01")
task.dueDate = null                          // clear due date
task.flagged = true
task.sequential = true
task.estimatedMinutes = 45
task.completedByChildren = true
task.shouldUseFloatingTimeZone = true
```

### Task Completion

```javascript
task.markComplete()                // mark done (now)
task.markComplete(new Date())      // mark done with specific date
task.markIncomplete()              // unmark
task.drop(false)                   // drop this occurrence
task.drop(true)                    // drop all occurrences
```

### Tag Assignment

```javascript
task.addTag(tag)                   // add single tag
task.addTags([tag1, tag2])         // add multiple
task.removeTag(tag)                // remove single
task.removeTags([tag1, tag2])      // remove multiple
task.clearTags()                   // remove all tags
```

### Project Status Changes

```javascript
project.status = Project.Status.Active
project.status = Project.Status.OnHold
project.status = Project.Status.Done
project.status = Project.Status.Dropped
project.markComplete()
project.markIncomplete()
```

### Repetition Rules

```javascript
// Set repetition
task.repetitionRule = new Task.RepetitionRule(
  "FREQ=WEEKLY",                                  // ICS rule string
  null,                                            // method (deprecated)
  Task.RepetitionScheduleType.Regularly,           // schedule type
  Task.AnchorDateKey.DueDate,                      // anchor
  true                                             // catch up automatically
)

// Clear repetition
task.repetitionRule = null

// Read repetition
if (task.repetitionRule) {
  task.repetitionRule.ruleString           // "FREQ=WEEKLY"
  task.repetitionRule.scheduleType         // enum
  task.repetitionRule.anchorDateKey        // enum
  task.repetitionRule.catchUpAutomatically // Boolean
  task.repetitionRule.firstDateAfterDate(new Date())  // next occurrence
}
```

### Notes

```javascript
task.note = "Replace entire note"
task.appendStringToNote("\nAppended line")     // append to existing
project.appendStringToNote("\nAppended line")
```

---

## 10. Perspectives

### Built-in Perspectives

```javascript
Perspective.BuiltIn.Inbox
Perspective.BuiltIn.Projects
Perspective.BuiltIn.Tags
Perspective.BuiltIn.Forecast
Perspective.BuiltIn.Flagged
Perspective.BuiltIn.Review
Perspective.BuiltIn.Nearby    // iOS only
Perspective.BuiltIn.all       // Array of all built-in
```

### Custom Perspectives

```javascript
Perspective.Custom.all                      // Array of all custom perspectives
Perspective.Custom.byName("My View")        // find by name
Perspective.Custom.byIdentifier("aS3jYumRtrm")  // find by ID

// Properties:
customPerspective.name          // String (read-only)
customPerspective.identifier    // String (read-only)
customPerspective.iconColor     // Color or null
```

### Navigating to Perspectives

```javascript
document.windows[0].perspective = Perspective.BuiltIn.Inbox
document.windows[0].perspective = Perspective.Custom.byName("Work")
```

### Listing All Perspectives

The bridge script uses `Perspective.all` which appears to combine both built-in and custom.
The documented approach is separate access via `Perspective.BuiltIn.all` and `Perspective.Custom.all`.

---

## 11. Identity and URLs

### Object Identity

```javascript
entity.id                  // ObjectIdentifier
entity.id.primaryKey       // String -- unique identifier
entity.id.objectClass      // Constructor (e.g., Task, Project)
```

### URL Access

```javascript
entity.url                 // URL or null (v4.5+)

// Resolve from URL
objectForURL(url)          // DatabaseObject or null
```

---

## 12. `evaluateJavascript` Bridge (JXA -> OmniJS)

From JXA, you can execute Omni Automation code inside OmniFocus:

```javascript
// JXA side:
const result = Application("OmniFocus").evaluateJavascript("flattenedProjects.length")

// With function:
const f = () => {
  return JSON.stringify(
    flattenedProjects.map(p => ({ id: p.id.primaryKey, name: p.name }))
  )
}
const json = Application("OmniFocus").evaluateJavascript(`(${f})()`)
const data = JSON.parse(json)
```

**Constraints:**
- Only primitives and JSON-serializable data cross the bridge
- OmniJS objects cannot be passed to JXA
- `argument` variable is NOT available in `evaluateJavascript` context (only in URL scheme scripts)
- Use `JSON.stringify()` on the OmniJS side and `JSON.parse()` on the JXA side

---

## 13. URL Scheme Script Execution

OmniFocus supports running scripts via URL scheme:

```
omnifocus://localhost/omnijs-run?script=<encoded_script>&arg=<encoded_argument>
```

- `script=` -- percent-encoded JavaScript code
- `&arg=` -- percent-encoded argument data (string, array, or object)
- Inside the script, `argument` contains the decoded `&arg=` value
- OmniFocus JSON-parses the `&arg=` parameter before making it available
- The `argument` variable is a **special placeholder** available only in the top-level script evaluation context
- Code loaded via `eval()` from a separate file does NOT have access to `argument`

---

## 14. Complete API Class List

From the OmniFocus API 3.13.1 reference, all available classes:

**Core Entity Classes:** Task, Project, Tag, Folder, Perspective, Perspective.BuiltIn, Perspective.Custom

**Base Classes:** Database, DatabaseObject, DatedObject, ActiveObject

**Collection Classes:** Array, TaskArray, ProjectArray, TagArray, FolderArray, SectionArray, Library, Tags, Inbox

**Status/Enum Classes:** Task.Status, Project.Status, Tag.Status, Folder.Status, ApplyResult, Task.RepetitionMethod, Task.RepetitionRule, Task.Notification, Task.Notification.Kind, Project.ReviewInterval

**Insertion Locations:** Task.ChildInsertionLocation, Tag.ChildInsertionLocation, Folder.ChildInsertionLocation

**UI Classes:** Window, DocumentWindow, Document, DatabaseDocument, Selection, ContentTree, SidebarTree, Tree, TreeNode, Form, Form.Field.*, Alert, SharePanel, MenuItem

**Formatting:** Formatter, Formatter.Date, Formatter.Decimal, Formatter.Duration, Decimal

**Date/Time:** Calendar, DateComponents, DateRange, TimeZone, ForecastDay, ForecastDay.Kind, ForecastDay.Status

**File I/O:** FileWrapper, FileWrapper.Type, FilePicker, FileSaver

**Network:** URL, URL.FetchRequest, URL.FetchResponse, URL.Components, URL.QueryItem, URL.Access, URL.Bookmark

**Data:** Data, Credentials, Crypto, Crypto.SHA256/384/512, StringEncoding, XML, XML.Document, XML.Element

**Style:** Style, Style.Attribute, NamedStyle, NamedStyle.List, Text, Text.FindOption, Text.Position, Text.Range, Color, ColorSpace, Image

**Utilities:** Application, Console, Device, DeviceType, Email, Error, Locale, Notification, ObjectIdentifier, Pasteboard, Pasteboard.Item, PlugIn, PlugIn.Action, PlugIn.Handler, PlugIn.Library, Preferences, Promise, Settings, Speech, Speech.Synthesizer, Speech.Utterance, Speech.Voice, Timer, TypeIdentifier, Version

---

## 15. Relevance to OmniFocus Operator Bridge

The existing `operatorBridgeScript.js` already correctly uses Omni Automation conventions:

1. **Direct property access** -- `p.name`, `t.tags.map(...)`, not `p.name()`
2. **Bare globals** -- `flattenedTasks`, `flattenedProjects`, not `document.flattenedProjects()`
3. **Enum comparison via identity** -- `s === Task.Status.Available`
4. **`argument` variable** -- receives the dispatch string via URL scheme `&arg=`
5. **File I/O via FileWrapper** -- writes JSON responses to the documents directory

The audit scripts (01-12) use **JXA style** because they are designed to run in JXA context (via `osascript`), NOT in the Omni Automation console.

---

## Sources

- [OmniFocus & Omni Automation Hub](https://omni-automation.com/omnifocus/index.html)
- [OmniFocus API 3.13.1 Reference](https://www.omni-automation.com/omnifocus/OF-API.html)
- [OmniFocus: The Big Picture](https://www.omni-automation.com/omnifocus/big-picture.html)
- [OmniFocus: Database](https://omni-automation.com/omnifocus/database.html)
- [OmniFocus: Database Object](https://omni-automation.com/omnifocus/database-object.html)
- [OmniFocus: Tasks](https://www.omni-automation.com/omnifocus/task.html)
- [OmniFocus: Projects](https://omni-automation.com/omnifocus/project.html)
- [OmniFocus: Tags](https://omni-automation.com/omnifocus/tag.html)
- [OmniFocus: Folders](https://omni-automation.com/omnifocus/folder.html)
- [OmniFocus: Perspectives](https://omni-automation.com/omnifocus/perspective.html)
- [OmniFocus: Finding Items (apply)](https://omni-automation.com/omnifocus/apply.html)
- [OmniFocus: Repeating Tasks](https://omni-automation.com/omnifocus/task-repeat.html)
- [OmniFocus: Application](https://omni-automation.com/omnifocus/application.html)
- [OmniFocus: Window](https://omni-automation.com/omnifocus/window.html)
- [OmniFocus: Tutorial](https://omni-automation.com/omnifocus/tutorial/index.html)
- [Omni Automation Console](https://omni-automation.com/console/index.html)
- [Omni Automation Script URLs](https://omni-automation.com/script-url/)
- [Omni Group Forums: JXA vs Omni Automation taskStatus](https://discourse.omnigroup.com/t/accessing-omnifocus-taskstatus-available-etc-using-jxa/65324)
- [Omni Group Forums: Returning data from Omni Automation](https://discourse.omnigroup.com/t/returning-data-from-omni-automation-script/70648)
