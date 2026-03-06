# Field Coverage: XML .ofocus vs Bridge (Complete)

> Every bridge field checked. Result: **0 fields impossible from XML.**

## Task Fields (32 fields)

| Field | XML Source | How |
|---|---|---|
| `id` | `<task id="...">` | Direct |
| `name` | `<name>` | Direct |
| `url` | — | Construct: `omnifocus:///task/{id}` |
| `note` | `<note><text><p><run><lit>` | Direct (rich-text extraction) |
| `added` | `<added>` | Direct |
| `modified` | `<modified>` | Direct |
| `active` | `<hidden>` | Compute: `false` only when self-dropped |
| `effectiveActive` | hierarchy + statuses | Compute: walk parent/project chain |
| `status` | — | Compute: Completed/Dropped/Blocked/DueSoon/Overdue/Next/Available |
| `completed` | `<completed>` | Compute: `true` if has date |
| `completedByChildren` | `<completed-by-children>` | Direct |
| `flagged` | `<flagged>` | Direct |
| `effectiveFlagged` | hierarchy | Compute: walk parent chain |
| `sequential` | `<order>` | Direct: `"sequential"` vs `"parallel"` |
| `dueDate` | `<due>` | Direct |
| `deferDate` | `<start>` | Direct (XML calls it "start") |
| `effectiveDueDate` | hierarchy | Compute: inherit from parent |
| `effectiveDeferDate` | hierarchy | Compute: inherit from parent |
| `completionDate` | `<completed>` | Direct |
| `effectiveCompletionDate` | hierarchy | Compute |
| `plannedDate` | `<planned>` | Direct |
| `effectivePlannedDate` | hierarchy | Compute |
| `dropDate` | `<hidden>` (with date) | Direct: hidden date IS the drop date |
| `effectiveDropDate` | hierarchy | Compute |
| `estimatedMinutes` | `<estimated-minutes>` | Direct |
| `hasChildren` | parent references | Compute: any task references this as parent |
| `inInbox` | `<inbox>` | Direct |
| `shouldUseFloatingTimeZone` | date format | Infer: no Z suffix = floating (always `true` in practice) |
| `repetitionRule.ruleString` | `<repetition-rule>` | Direct (iCal RRULE) |
| `repetitionRule.scheduleType` | `<repetition-schedule-type>` | Direct |
| `repetitionRule.anchorDateKey` | `<repetition-anchor-date>` | Direct |
| `repetitionRule.catchUpAutomatically` | `<catch-up-automatically>` | Direct |
| `project` | parent chain | Compute: walk up to find project |
| `parent` | `<task idref="...">` | Direct |
| `tags[]` | `<task-to-tag>` elements | Direct |

## Project Fields (additional to task fields)

| Field | XML Source | How |
|---|---|---|
| `status` | `<project><status>` | Direct: active/inactive/done/dropped |
| `taskStatus` | — | Compute: same as task status |
| `containsSingletonActions` | `<project><singleton>` | Direct |
| `lastReviewDate` | `<project><last-review>` | Direct |
| `nextReviewDate` | `<project><next-review>` | Direct |
| `reviewInterval.steps` | `<project><review-interval>` | Parse: extract number from `~2w` |
| `reviewInterval.unit` | `<project><review-interval>` | Parse: `d`/`w`/`m`/`y` suffix |
| `nextTask` | — | Compute: first eligible child in sequential project |
| `folder` | `<project><folder idref>` | Direct |

## Tag Fields

| Field | XML Source | How |
|---|---|---|
| `id` | `<context id="...">` | Direct |
| `name` | `<name>` | Direct |
| `url` | — | Construct: `omnifocus:///tag/{id}` |
| `added`/`modified` | `<added>`/`<modified>` | Direct |
| `active` | `<hidden>` | Compute: `false` only for Dropped |
| `effectiveActive` | — | Compute: same as `active` (tags don't inherit) |
| `status` | `<hidden>` + `<prohibits-next-action>` | Compute: Active/OnHold/Dropped |
| `allowsNextAction` | `<prohibits-next-action>` | Direct (inverted) |
| `childrenAreMutuallyExclusive` | `<children-are-mutually-exclusive>` | Direct |
| `parent` | `<context idref="...">` | Direct |

## Folder Fields

| Field | XML Source | How |
|---|---|---|
| `id` | `<folder id="...">` | Direct |
| `name` | `<name>` | Direct |
| `url` | — | Construct: `omnifocus:///folder/{id}` |
| `added`/`modified` | `<added>`/`<modified>` | Direct |
| `active` | `<hidden>` | Compute: `false` only for Dropped |
| `effectiveActive` | hierarchy | Compute: walk parent folder chain |
| `status` | `<hidden>` | Compute: Active/Dropped |
| `parent` | `<folder idref="...">` | Direct |

## Perspective Fields

| Field | XML Source | How |
|---|---|---|
| `id` | `<perspective id="...">` | Direct |
| `name` | plist dict `name` key | Direct |
