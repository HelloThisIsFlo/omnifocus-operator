---
suite: batch-processing
display: Batch Processing
test_count: 12

discovery:
  needs:
    - type: project
      label: gm-project
      filters: [active]

setup: |
  ### Discovery

  Use the discovered `gm-project` as the hierarchy container. Its real ID replaces `id-project`
  in the batch payload. Verify that the GM project is reasonably empty — if it already contains
  tasks, they will appear in the `list_tasks` ordering check and invalidate Test 1b. Warn the
  user and wait for a green light before proceeding.

  ### Create 50 identical tasks in the inbox (Test 1 only)

  In a SINGLE `add_tasks` call (50 items, all named "UAT-Batch-Hero", no parent):

  ```json
  { "items": [
    { "name": "UAT-Batch-Hero" },
    { "name": "UAT-Batch-Hero" },
    ... (repeat 50 times total)
  ] }
  ```

  Record the 50 IDs from the response array in order. Position 0 is the first result's ID,
  position 49 is the last. You will use these positions to substitute placeholder IDs in Test 1a.

  ### Create per-item semantics fixtures (Test 2 only)

  In a SEPARATE `add_tasks` call, create this structure in the inbox:

  ```
  UAT-Batch-PerItem (inbox parent)
  +-- PI-EditA
  +-- PI-EditB
  +-- PI-EditC
  ```

  Store the child IDs as **pi-a**, **pi-b**, **pi-c** — used by Test 2 edit scenarios.

manual_actions:
  - "Verify that `gm-project` is empty (or contains only pre-existing fixtures unrelated to this test). If it has tasks that would appear in the ordering check, ask the user to select a different project or clear it before proceeding."
---

# Batch Processing Test Suite

Tests the batch capabilities of `add_tasks` and `edit_tasks`: the 50-item "Hero's Journey" mega-batch (Test 1) plus per-item semantics — best-effort vs fail-fast, response shape, "Task N:" error prefix, skipped-item warnings, sequential commit, and cross-item name-ref resolution (Test 2).

## Conventions

- **Inbox for creation, GM project for result (Test 1).** The 50 tasks are created flat in the inbox (all identically named), then renamed, moved into a GM project, and organized into a hierarchy by the mega-batch call.
- **Inbox only (Test 2).** Per-item semantics tests create and edit tasks in the inbox. The `UAT-Batch-PerItem` parent is the anchor; ad-hoc tasks (e.g., `B2a-AddOK-1`) are created inline and consolidated under the standard cleanup umbrella.
- **Batch calls.** Both `add_tasks` and `edit_tasks` accept up to 50 items. Setup uses `add_tasks` with 50 items; Test 1 uses `edit_tasks` with 50 items; Test 2 uses batches of 1–3 items.
- **Result array shape.** Every batch response is a flat array: `{ status: "success" | "error" | "skipped", id?, name?, warnings?, error? }` per item.
- **Field absence vs null.** Response items use field **absence** (key not present) — not `null` — to signal unavailable fields. A failed `add_tasks` item has no `id` key at all, not `id: null`.
- **edit_tasks is fail-fast.** First error stops the batch; remaining items get `status: "skipped"` with a warning referencing the failing item by 1-indexed position.
- **add_tasks is best-effort.** All items processed regardless of earlier failures.
- **"Task N:" prefix on per-item errors.** Both schema and service errors use 1-indexed positional prefix (e.g., `"Task 3: Invalid tag 'Foo'"`).
- **ID substitution is positional (Test 1).** All 50 tasks are identical at creation — substitute by array position, not by name.
- **Behavioral warning/error assertions.** Warning and error text is asserted by presence + fluency + no-internals (no `type=`, `pydantic`, `input_value`, `_Unset`). Exact strings are NOT asserted so the suite survives wording improvements.
- **Run error-expecting calls individually.** Claude Code cancels sibling MCP calls when one errors — never batch error-expecting calls alongside success calls at the MCP-call level. (This is different from a batch *within* one MCP call, which is the whole point of this suite.)

## ID Substitution Reference

The `add_tasks` setup response returns IDs in array order. Map each response position to the corresponding placeholder ID in the batch payload:

| Position | Placeholder ID in payload |
|---|---|
| 0 | `id-task-1` |
| 1 | `id-task-2` |
| 2 | `id-task-3` |
| 3 | `id-task-4` |
| 4 | `id-task-5` |
| 5 | `id-task-6` |
| 6 | `id-task-7` |
| 7 | `id-task-8` |
| 8 | `id-task-9` |
| 9 | `id-task-10` |
| 10 | `id-task-11` |
| 11 | `id-task-12` |
| 12 | `id-task-13` |
| 13 | `id-task-14` |
| 14 | `id-task-15` |
| 15 | `id-task-16` |
| 16 | `id-task-17` |
| 17 | `id-task-18` |
| 18 | `id-task-19` |
| 19 | `id-task-20` |
| 20 | `id-task-21` |
| 21 | `id-task-22` |
| 22 | `id-task-23` |
| 23 | `id-task-24` |
| 24 | `id-task-25` |
| 25 | `id-task-26` |
| 26 | `id-task-27` |
| 27 | `id-task-28` |
| 28 | `id-task-29` |
| 29 | `id-task-30` |
| 30 | `id-task-31` |
| 31 | `id-task-32` |
| 32 | `id-task-33` |
| 33 | `id-task-34` |
| 34 | `id-task-35` |
| 35 | `id-task-36` |
| 36 | `id-task-37` |
| 37 | `id-task-38` |
| 38 | `id-task-39` |
| 39 | `id-task-40` |
| 40 | `id-task-41` |
| 41 | `id-task-42` |
| 42 | `id-task-43` |
| 43 | `id-task-44` |
| 44 | `id-task-45` |
| 45 | `id-task-46` |
| 46 | `id-task-47` |
| 47 | `id-task-48` |
| 48 | `id-task-49` |
| 49 | `id-task-50` |
| — | `id-project` ← **GM project container** — replace with `gm-project.id` from discovery (not a task) |

## Tests

### 1. Hero's Journey: 50-Item Mega-Batch

#### Test 1a: Execute the mega-batch
1. From the setup `add_tasks` response, read the 50 IDs in array order (position 0–49).
2. Scan the payload below. Replace **every** placeholder ID:
   - In each item's `"id"` field: look up its position in the table above → use `response[position].id`.
   - In every move target value (`"beginning"`, `"ending"`, `"before"`, `"after"`): find the placeholder in the table, use the corresponding real ID.
   - Replace `"id-project"` with `gm-project.id` from discovery.
3. Run `edit_tasks` with the substituted 50-item payload:
```json
[
  {
    "id": "id-task-1",
    "name": "Strike true",
    "estimatedMinutes": 37,
    "note": "One chance. Make it count.",
    "dueDate": "2026-07-04T12:00:00",
    "actions": {
      "move": {
        "ending": "id-task-4"
      }
    }
  },
  {
    "id": "id-task-2",
    "name": "Find the weakness",
    "estimatedMinutes": 36,
    "actions": {
      "move": {
        "beginning": "id-task-4"
      }
    }
  },
  {
    "id": "id-task-3",
    "name": "Dodge the charge",
    "estimatedMinutes": 35,
    "actions": {
      "move": {
        "beginning": "id-task-4"
      }
    }
  },
  {
    "id": "id-task-4",
    "name": "Meet the minotaur",
    "estimatedMinutes": 34,
    "actions": {
      "move": {
        "ending": "id-task-11"
      }
    }
  },
  {
    "id": "id-task-5",
    "name": "Follow the thread",
    "estimatedMinutes": 33,
    "actions": {
      "move": {
        "beginning": "id-task-11"
      }
    }
  },
  {
    "id": "id-task-6",
    "name": "Enter the maze",
    "estimatedMinutes": 32,
    "actions": {
      "move": {
        "before": "id-task-5"
      }
    }
  },
  {
    "id": "id-task-7",
    "name": "Prove your worth",
    "estimatedMinutes": 30,
    "note": "Show them what you're made of",
    "actions": {
      "move": {
        "ending": "id-task-10"
      }
    }
  },
  {
    "id": "id-task-8",
    "name": "Answer three questions",
    "estimatedMinutes": 29,
    "actions": {
      "move": {
        "before": "id-task-7"
      }
    }
  },
  {
    "id": "id-task-9",
    "name": "Approach the gate",
    "estimatedMinutes": 28,
    "actions": {
      "move": {
        "beginning": "id-task-10"
      }
    }
  },
  {
    "id": "id-task-10",
    "name": "Scene 5: The Guardian",
    "estimatedMinutes": 27,
    "flagged": true,
    "actions": {
      "move": {
        "beginning": "id-task-48"
      }
    }
  },
  {
    "id": "id-task-11",
    "name": "Scene 6: The Labyrinth",
    "estimatedMinutes": 31,
    "flagged": true,
    "actions": {
      "move": {
        "after": "id-task-10"
      }
    }
  },
  {
    "id": "id-task-12",
    "name": "Rest at last",
    "estimatedMinutes": 50,
    "note": "And so the journey ends",
    "actions": {
      "move": {
        "ending": "id-task-50"
      }
    }
  },
  {
    "id": "id-task-13",
    "name": "Plant the tree",
    "estimatedMinutes": 49,
    "actions": {
      "move": {
        "beginning": "id-task-50"
      }
    }
  },
  {
    "id": "id-task-14",
    "name": "Train the apprentice",
    "estimatedMinutes": 48,
    "actions": {
      "move": {
        "beginning": "id-task-50"
      }
    }
  },
  {
    "id": "id-task-15",
    "name": "Write the chronicle",
    "estimatedMinutes": 47,
    "dueDate": "2026-05-01T17:00:00",
    "repetitionRule": {
      "frequency": {
        "type": "weekly",
        "onDays": [
          "MO",
          "FR"
        ]
      },
      "schedule": "regularly_with_catch_up",
      "basedOn": "due_date"
    },
    "actions": {
      "move": {
        "beginning": "id-task-50"
      }
    }
  },
  {
    "id": "id-task-16",
    "name": "Sharpen sword",
    "estimatedMinutes": 10,
    "actions": {
      "move": {
        "ending": "id-task-18"
      }
    }
  },
  {
    "id": "id-task-17",
    "name": "Pack food",
    "estimatedMinutes": 9,
    "actions": {
      "move": {
        "beginning": "id-task-18"
      }
    }
  },
  {
    "id": "id-task-18",
    "name": "Gather supplies",
    "estimatedMinutes": 8,
    "actions": {
      "move": {
        "ending": "id-task-24"
      }
    }
  },
  {
    "id": "id-task-19",
    "name": "Receive the message",
    "estimatedMinutes": 7,
    "actions": {
      "move": {
        "beginning": "id-task-24"
      }
    }
  },
  {
    "id": "id-task-20",
    "name": "Find the map",
    "estimatedMinutes": 5,
    "actions": {
      "move": {
        "ending": "id-task-23"
      }
    }
  },
  {
    "id": "id-task-21",
    "name": "Check surroundings",
    "estimatedMinutes": 4,
    "actions": {
      "move": {
        "beginning": "id-task-23"
      }
    }
  },
  {
    "id": "id-task-22",
    "name": "Open eyes",
    "estimatedMinutes": 3,
    "actions": {
      "move": {
        "beginning": "id-task-23"
      }
    }
  },
  {
    "id": "id-task-23",
    "name": "Scene 1: The Awakening",
    "estimatedMinutes": 2,
    "flagged": true,
    "actions": {
      "move": {
        "ending": "id-task-46"
      }
    }
  },
  {
    "id": "id-task-24",
    "name": "Scene 2: The Call",
    "estimatedMinutes": 6,
    "flagged": true,
    "actions": {
      "move": {
        "after": "id-task-23"
      }
    }
  },
  {
    "id": "id-task-25",
    "name": "Read the inscription",
    "estimatedMinutes": 24,
    "actions": {
      "move": {
        "ending": "id-task-28"
      }
    }
  },
  {
    "id": "id-task-26",
    "name": "Light the torch",
    "estimatedMinutes": 23,
    "actions": {
      "move": {
        "beginning": "id-task-28"
      }
    }
  },
  {
    "id": "id-task-27",
    "name": "Solve the riddle",
    "estimatedMinutes": 25,
    "flagged": true,
    "note": "The answer was inside you all along",
    "dueDate": "2026-12-31T23:59:00",
    "deferDate": "2026-06-01T09:00:00",
    "plannedDate": "2026-09-15T10:00:00",
    "repetitionRule": {
      "frequency": {
        "type": "monthly",
        "on": {
          "last": "friday"
        }
      },
      "schedule": "regularly_with_catch_up",
      "basedOn": "due_date"
    },
    "actions": {
      "move": {
        "after": "id-task-25"
      }
    }
  },
  {
    "id": "id-task-28",
    "name": "Discover the cave",
    "estimatedMinutes": 22,
    "actions": {
      "move": {
        "ending": "id-task-38"
      }
    }
  },
  {
    "id": "id-task-29",
    "name": "Find shelter",
    "estimatedMinutes": 21,
    "actions": {
      "move": {
        "beginning": "id-task-38"
      }
    }
  },
  {
    "id": "id-task-30",
    "name": "Face the storm",
    "estimatedMinutes": 20,
    "note": "The wind howls with fury",
    "actions": {
      "move": {
        "beginning": "id-task-38"
      }
    }
  },
  {
    "id": "id-task-31",
    "name": "Begin the climb",
    "estimatedMinutes": 19,
    "actions": {
      "move": {
        "beginning": "id-task-38"
      }
    }
  },
  {
    "id": "id-task-32",
    "name": "Navigate rapids",
    "estimatedMinutes": 17,
    "actions": {
      "move": {
        "ending": "id-task-34"
      }
    }
  },
  {
    "id": "id-task-33",
    "name": "Build a raft",
    "estimatedMinutes": 16,
    "actions": {
      "move": {
        "before": "id-task-32"
      }
    }
  },
  {
    "id": "id-task-34",
    "name": "Cross the river",
    "estimatedMinutes": 15,
    "actions": {
      "move": {
        "ending": "id-task-37"
      }
    }
  },
  {
    "id": "id-task-35",
    "name": "Meet the guide",
    "estimatedMinutes": 14,
    "actions": {
      "move": {
        "beginning": "id-task-37"
      }
    }
  },
  {
    "id": "id-task-36",
    "name": "Enter the woods",
    "estimatedMinutes": 13,
    "actions": {
      "move": {
        "before": "id-task-35"
      }
    }
  },
  {
    "id": "id-task-37",
    "name": "Scene 3: The Forest",
    "estimatedMinutes": 12,
    "flagged": true,
    "actions": {
      "move": {
        "ending": "id-task-47"
      }
    }
  },
  {
    "id": "id-task-38",
    "name": "Scene 4: The Mountain",
    "estimatedMinutes": 18,
    "flagged": true,
    "actions": {
      "move": {
        "after": "id-task-37"
      }
    }
  },
  {
    "id": "id-task-39",
    "name": "Collapse the tunnel",
    "estimatedMinutes": 41,
    "dueDate": "2026-08-15T18:00:00",
    "actions": {
      "move": {
        "ending": "id-task-44"
      }
    }
  },
  {
    "id": "id-task-40",
    "name": "Run for the exit",
    "estimatedMinutes": 40,
    "actions": {
      "move": {
        "beginning": "id-task-44"
      }
    }
  },
  {
    "id": "id-task-41",
    "name": "Tell the tale",
    "estimatedMinutes": 45,
    "actions": {
      "move": {
        "ending": "id-task-45"
      }
    }
  },
  {
    "id": "id-task-42",
    "name": "Reunite with friends",
    "estimatedMinutes": 44,
    "actions": {
      "move": {
        "beginning": "id-task-45"
      }
    }
  },
  {
    "id": "id-task-43",
    "name": "See the village",
    "estimatedMinutes": 43,
    "note": "Home at last",
    "actions": {
      "move": {
        "beginning": "id-task-45"
      }
    }
  },
  {
    "id": "id-task-44",
    "name": "Scene 7: The Escape",
    "estimatedMinutes": 39,
    "flagged": true,
    "actions": {
      "move": {
        "ending": "id-task-49"
      }
    }
  },
  {
    "id": "id-task-45",
    "name": "Scene 8: The Homecoming",
    "estimatedMinutes": 42,
    "flagged": true,
    "actions": {
      "move": {
        "after": "id-task-44"
      }
    }
  },
  {
    "id": "id-task-46",
    "name": "Act I: The Setup",
    "estimatedMinutes": 1,
    "flagged": true,
    "actions": {
      "move": {
        "beginning": "id-project"
      }
    }
  },
  {
    "id": "id-task-47",
    "name": "Act II: The Journey",
    "estimatedMinutes": 11,
    "flagged": true,
    "actions": {
      "move": {
        "after": "id-task-46"
      }
    }
  },
  {
    "id": "id-task-48",
    "name": "Act III: The Trial",
    "estimatedMinutes": 26,
    "flagged": true,
    "actions": {
      "move": {
        "after": "id-task-47"
      }
    }
  },
  {
    "id": "id-task-49",
    "name": "Act IV: The Return",
    "estimatedMinutes": 38,
    "flagged": true,
    "actions": {
      "move": {
        "after": "id-task-48"
      }
    }
  },
  {
    "id": "id-task-50",
    "name": "Act V: The Legacy",
    "estimatedMinutes": 46,
    "flagged": true,
    "actions": {
      "move": {
        "after": "id-task-49"
      }
    }
  }
]
```

4. PASS if: response is an array of exactly 50 items, **all** have `"status": "success"`, none have `"status": "error"` or `"status": "skipped"`.

#### Test 1b: Verify outline order
1. `list_tasks` with `project: "<gm-project-id>"`, `include: ["estimatedMinutes"]`, `availability: "ALL"`.
2. PASS if: response contains exactly 50 tasks with `estimatedMinutes` values 1 through 50 appearing in that exact ascending sequence (depth-first outline order proves the hierarchy was built correctly).

**Expected outline order for reference:**
```
1  — Act I: The Setup
2  —   Scene 1: The Awakening
3  —     Open eyes
4  —     Check surroundings
5  —     Find the map
6  —   Scene 2: The Call
7  —     Receive the message
8  —     Gather supplies
9  —       Pack food
10 —       Sharpen sword
11 — Act II: The Journey
12 —   Scene 3: The Forest
13 —     Enter the woods
14 —     Meet the guide
15 —     Cross the river
16 —       Build a raft
17 —       Navigate rapids
18 —   Scene 4: The Mountain
19 —     Begin the climb
20 —     Face the storm
21 —     Find shelter
22 —     Discover the cave
23 —       Light the torch
24 —       Read the inscription
25 —       Solve the riddle
26 — Act III: The Trial
27 —   Scene 5: The Guardian
28 —     Approach the gate
29 —     Answer three questions
30 —     Prove your worth
31 —   Scene 6: The Labyrinth
32 —     Enter the maze
33 —     Follow the thread
34 —     Meet the minotaur
35 —       Dodge the charge
36 —       Find the weakness
37 —       Strike true
38 — Act IV: The Return
39 —   Scene 7: The Escape
40 —     Run for the exit
41 —     Collapse the tunnel
42 —   Scene 8: The Homecoming
43 —     See the village
44 —     Reunite with friends
45 —     Tell the tale
46 — Act V: The Legacy
47 —     Train the apprentice
48 —     Plant the tree
49 —     Write the chronicle
50 —     Rest at last
```

### 2. Per-Item Semantics

These tests target the per-item response envelope and failure semantics that distinguish the two batch-enabled tools. Each test uses small batches (1–3 items) so assertions focus on shape rather than scale.

#### Test 2a: add_tasks best-effort — middle item fails, others still processed
1. `add_tasks` with 3 items:
   ```json
   { "items": [
     { "name": "B2a-AddOK-1" },
     { "name": "B2a-AddFail-2", "tags": ["B2a-NonexistentTag-DoesNotExist"] },
     { "name": "B2a-AddOK-3" }
   ] }
   ```
2. PASS if:
   - response is an array of exactly 3 items
   - `items[0].status == "success"` with `id` present and `name == "B2a-AddOK-1"`
   - `items[1].status == "error"` with an `error` field that is fluent (mentions the invalid tag), no internals leak
   - `items[2].status == "success"` with `id` present and `name == "B2a-AddOK-3"` — proving item 2's failure did NOT block item 3 (best-effort contract, BATCH-02)
   - `list_tasks` confirms `B2a-AddOK-1` and `B2a-AddOK-3` exist in OmniFocus; `B2a-AddFail-2` does NOT

#### Test 2b: add_tasks best-effort — first item fails, later items still processed
1. `add_tasks` with 2 items (first invalid):
   ```json
   { "items": [
     { "name": "B2b-AddFail-1", "tags": ["B2b-NonexistentTag-DoesNotExist"] },
     { "name": "B2b-AddOK-2" }
   ] }
   ```
2. PASS if:
   - `items[0].status == "error"`
   - `items[1].status == "success"` with `id` and `name == "B2b-AddOK-2"` — a first-item failure must NOT short-circuit `add_tasks` (symmetric with Test 2a, guards against regression to fail-fast behavior)

#### Test 2c: add_tasks failed item has NO id field (absence, not null)
1. `add_tasks` with 1 item guaranteed to fail at service layer:
   ```json
   { "items": [{ "name": "B2c-AddFail", "tags": ["B2c-NonexistentTag-DoesNotExist"] }] }
   ```
2. PASS if:
   - response array has 1 item
   - `items[0].status == "error"`
   - the response object does NOT contain an `id` key at all (field absence, not `id: null`)
   - the response object does NOT contain a `name` key at all (same absence contract)
   - an `error` field IS present and fluent; no internals leak (BATCH-05)

#### Test 2d: per-item error uses "Task N:" prefix (1-indexed)
1. `add_tasks` with 3 items; only the 3rd is invalid:
   ```json
   { "items": [
     { "name": "B2d-OK-1" },
     { "name": "B2d-OK-2" },
     { "name": "B2d-Fail-3", "tags": ["B2d-NonexistentTag-DoesNotExist"] }
   ] }
   ```
2. PASS if:
   - `items[2].status == "error"`
   - `items[2].error` text starts with `"Task 3:"` (1-indexed positional prefix); the remainder is fluent and mentions the failing tag; no internals leak

#### Test 2e: edit_tasks fail-fast — middle item fails, later items skipped
1. Pre-state: ensure `pi-a`, `pi-b`, `pi-c` are at their fixture names (`PI-EditA`, `PI-EditB`, `PI-EditC`).
2. `edit_tasks` with 3 items:
   ```json
   { "items": [
     { "id": "<pi-a>", "name": "PI-EditA-B2e" },
     { "id": "NONEXISTENT_ID_B2e", "name": "Impossible" },
     { "id": "<pi-c>", "name": "PI-EditC-B2e" }
   ] }
   ```
3. PASS if:
   - response is an array of exactly 3 items
   - `items[0].status == "success"` with `id == <pi-a>` and `name == "PI-EditA-B2e"` — item 1 was committed before the failure
   - `items[1].status == "error"` with `error` present (fluent; "Task 2:" prefix; no internals leak)
   - `items[2].status == "skipped"` with a `warnings` array; at least one warning is fluent, references the failing item by 1-indexed position (mentions `task 2`), no internals leak
   - `get_task(<pi-a>)` shows the new name `"PI-EditA-B2e"` (committed)
   - `get_task(<pi-c>)` shows the ORIGINAL name `"PI-EditC"` (skip = no write, not a rollback of earlier work)
4. Cleanup: `edit_tasks` on `<pi-a>` with `{ "name": "PI-EditA" }` to restore the fixture name.

#### Test 2f: edit_tasks fail-fast — first item fails, all remaining skipped
1. Pre-state: fixtures at original names.
2. `edit_tasks` with 3 items (first invalid):
   ```json
   { "items": [
     { "id": "NONEXISTENT_ID_B2f", "name": "Impossible" },
     { "id": "<pi-b>", "name": "PI-EditB-B2f" },
     { "id": "<pi-c>", "name": "PI-EditC-B2f" }
   ] }
   ```
3. PASS if:
   - `items[0].status == "error"` with error present ("Task 1:" prefix, fluent, no internals leak)
   - `items[1].status == "skipped"` with warning referencing task 1
   - `items[2].status == "skipped"` with warning referencing task 1
   - `get_task(<pi-b>)` and `get_task(<pi-c>)` both show the ORIGINAL names — nothing was committed because the first item failed immediately (edge case of the fail-fast contract)

#### Test 2g: edit_tasks skipped item retains input `id`
1. `edit_tasks` with 2 items (first invalid):
   ```json
   { "items": [
     { "id": "NONEXISTENT_ID_B2g", "name": "x" },
     { "id": "<pi-a>", "name": "Unused" }
   ] }
   ```
2. PASS if:
   - `items[1].status == "skipped"`
   - `items[1].id == "<pi-a>"` — the input ID is preserved in the skipped response (contrast with failed `add_tasks` items where `id` is absent; for edit we ALWAYS know which task was targeted, BATCH-05)
   - `get_task(<pi-a>)` shows the original `"PI-EditA"` name (skip = no mutation)

#### Test 2h: edit_tasks sequential commit — same task edited twice in one batch
1. `edit_tasks` with 2 items targeting the same task:
   ```json
   { "items": [
     { "id": "<pi-a>", "name": "B2h-First" },
     { "id": "<pi-a>", "name": "B2h-Final" }
   ] }
   ```
2. PASS if:
   - `items[0].status == "success"` AND `items[1].status == "success"` (both commit)
   - `get_task(<pi-a>)` returns `name == "B2h-Final"` — the second edit sees item 1's committed state and overwrites (BATCH-07, BATCH-08: serial order, same-task edits permitted)
3. Cleanup: `edit_tasks` on `<pi-a>` with `{ "name": "PI-EditA" }` to restore.

#### Test 2i: add_tasks cross-item references resolve by name (serial execution)
Items in a batch are processed serially, which means each item's name resolution runs AFTER prior items have committed. So while an item cannot reference a sibling by ID (IDs don't exist yet), it CAN reference a sibling by NAME — the name resolver finds the just-created task.

Precondition: choose a parent name unique enough that it won't collide with anything pre-existing in your OmniFocus database. If there's already a task somewhere named "B2i-Parent-Unique-XYZ", change the suffix.

1. `add_tasks` with 2 items where item 2 references item 1's just-created task by name:
   ```json
   { "items": [
     { "name": "B2i-Parent-Unique-XYZ" },
     { "name": "B2i-Child", "parent": "B2i-Parent-Unique-XYZ" }
   ] }
   ```
2. PASS if:
   - `items[0].status == "success"` with `id` present — call it `parent-id`
   - `items[1].status == "success"` with `id` present — call it `child-id`
   - `get_task(child-id)` returns `parent.task.id == parent-id` AND `parent.task.name == "B2i-Parent-Unique-XYZ"` — the child was parented under item 1's just-created task via serial-execution name resolution
   - Equivalently, `list_tasks` with `parent: "B2i-Parent-Unique-XYZ"` returns `B2i-Child` in its items array

**Caveat — ID refs still don't work.** This test exercises name refs specifically. Referencing a sibling by ID (e.g. `parent: "<item-1-expected-id>"`) cannot work in the same batch because the ID only exists after item 1 commits and returns its response. For hierarchies, prefer name refs with unique-enough names, or use sequential calls when names might collide. The spec/tool-description currently under-specifies this nuance (see the linked todo).

#### Test 2j: per-item result strips empty `warnings` field
1. `add_tasks` with 2 clean items (no warnings expected):
   ```json
   { "items": [
     { "name": "B2j-Clean-1" },
     { "name": "B2j-Clean-2" }
   ] }
   ```
2. PASS if:
   - `items[0].status == "success"` AND `items[1].status == "success"`
   - Neither response item contains a `warnings` key (the empty/null warnings array is stripped per Phase 53 response shaping — the per-item envelope is subject to the same absence contract as top-level responses, BATCH-06)
   - Neither item contains an `error` key (same absence contract for unused fields on success)

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Mega-batch: execute | 50-item `edit_tasks`; all 50 return `status: "success"` | |
| 1b | Mega-batch: ordering | `list_tasks` on GM project shows `estimatedMinutes` 1→50 in depth-first outline order | |
| 2a | add_tasks best-effort: middle fail | Items 1, 3 succeed; item 2 errors; best-effort does NOT short-circuit | |
| 2b | add_tasks best-effort: first fail | Item 1 errors; item 2 still succeeds (first-item failure doesn't block) | |
| 2c | add_tasks failed: id/name absent | Failed add response has NO `id` and NO `name` keys (absence, not null) | |
| 2d | Per-item error: "Task N:" prefix | Item 3 error text begins with `Task 3:` (1-indexed) | |
| 2e | edit_tasks fail-fast: middle fail | [success, error, skipped]; item 1 committed, item 3 unchanged; skip warning references task 2 | |
| 2f | edit_tasks fail-fast: first fail | All remaining items skipped; no commits; skip warnings reference task 1 | |
| 2g | edit_tasks skipped: id retained | Skipped edit item keeps input `id` (contrast with failed add) | |
| 2h | edit_tasks sequential commit | Same task edited twice; second edit overwrites first (serial order) | |
| 2i | Cross-item ref: name resolution | Item 2 references item 1 by unique name; child is parented under just-created sibling via serial-execution name resolution | |
| 2j | Per-item stripping: empty warnings | Success items have no `warnings` key when empty (absence contract applies to per-item envelope) | |
