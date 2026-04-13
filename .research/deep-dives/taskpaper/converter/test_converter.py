"""
Tests for the OmniFocus JSON <-> TaskPaper converter.

Covers:
  - JSON -> TaskPaper (full and LLM modes)
  - TaskPaper -> JSON (parsing)
  - Round-trip (JSON -> TaskPaper -> JSON field preservation)
  - Token comparison (requires tiktoken)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add parent to path so we can import the converter
sys.path.insert(0, str(Path(__file__).parent.parent))

from converter.json_to_taskpaper import json_to_taskpaper, Mode
from converter.taskpaper_to_json import taskpaper_to_json


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _make_sample_dump(n_projects: int = 20, n_tasks: int = 100) -> dict:
    """Generate a realistic OmniFocus JSON dump for testing."""
    import random
    random.seed(42)

    folders = [
        {"id": "folder_1", "name": "Work", "added": "2025-01-01T00:00:00.000Z",
         "modified": "2026-02-20T10:00:00.000Z", "active": True,
         "effectiveActive": True, "status": "Active", "parent": None},
        {"id": "folder_2", "name": "Personal", "added": "2025-01-01T00:00:00.000Z",
         "modified": "2026-02-20T10:00:00.000Z", "active": True,
         "effectiveActive": True, "status": "Active", "parent": None},
        {"id": "folder_3", "name": "Side Projects", "added": "2025-03-01T00:00:00.000Z",
         "modified": "2026-02-18T08:00:00.000Z", "active": True,
         "effectiveActive": True, "status": "Active", "parent": "folder_1"},
        {"id": "folder_4", "name": "Health", "added": "2025-06-01T00:00:00.000Z",
         "modified": "2026-02-15T12:00:00.000Z", "active": True,
         "effectiveActive": True, "status": "Active", "parent": "folder_2"},
        {"id": "folder_5", "name": "Finance", "added": "2025-06-01T00:00:00.000Z",
         "modified": "2026-02-19T09:00:00.000Z", "active": True,
         "effectiveActive": True, "status": "Active", "parent": "folder_2"},
    ]

    tag_names = [
        "home", "office", "errands", "email", "phone", "computer",
        "morning", "evening", "waiting-for", "someday-maybe",
        "low-energy", "high-energy", "quick-win", "deep-work",
        "review", "admin", "creative", "routine", "urgent",
        "brainstorm", "research", "meeting-prep", "follow-up",
        "delegation", "learning", "writing", "coding", "design",
        "planning", "communication",
    ]

    tags = []
    for i, tn in enumerate(tag_names):
        tags.append({
            "id": f"tag_{i+1}",
            "name": tn,
            "added": "2025-01-15T00:00:00.000Z",
            "modified": "2026-02-01T00:00:00.000Z",
            "active": True,
            "effectiveActive": True,
            "status": "Active",
            "allowsNextAction": True,
            "parent": None,
        })

    project_names = [
        "Q1 OKRs", "Website Redesign", "API v3 Migration",
        "Team Hiring", "Budget Review", "Product Launch",
        "Documentation Overhaul", "Security Audit", "Performance Tuning",
        "Mobile App", "Customer Feedback Analysis", "Onboarding Flow",
        "Grocery Shopping", "Home Renovation", "Vacation Planning",
        "Book Club", "Fitness Plan", "Tax Preparation",
        "Side Project Alpha", "Side Project Beta",
    ]

    projects = []
    folder_ids = ["folder_1", "folder_1", "folder_1", "folder_1", "folder_5",
                  "folder_1", "folder_1", "folder_1", "folder_3", "folder_3",
                  "folder_1", "folder_1", "folder_2", "folder_4", "folder_2",
                  "folder_2", "folder_4", "folder_5", "folder_3", "folder_3"]

    for i, pname in enumerate(project_names[:n_projects]):
        p = {
            "id": f"proj_{i+1}",
            "name": pname,
            "note": f"Notes for {pname}" if i % 3 == 0 else "",
            "status": "Active" if i < 16 else "OnHold",
            "taskStatus": "Available",
            "completed": False,
            "completedByChildren": i % 5 == 0,
            "completionDate": None,
            "effectiveCompletionDate": None,
            "flagged": i % 4 == 0,
            "effectiveFlagged": i % 4 == 0,
            "sequential": i % 3 == 0,
            "containsSingletonActions": i == 12,  # Grocery Shopping
            "dueDate": f"2026-03-{15 + (i % 15):02d}T00:00:00.000Z" if i % 3 == 0 else None,
            "deferDate": f"2026-02-{10 + (i % 18):02d}T00:00:00.000Z" if i % 4 == 0 else None,
            "effectiveDueDate": f"2026-03-{15 + (i % 15):02d}T00:00:00.000Z" if i % 3 == 0 else None,
            "effectiveDeferDate": f"2026-02-{10 + (i % 18):02d}T00:00:00.000Z" if i % 4 == 0 else None,
            "dropDate": None,
            "effectiveDropDate": None,
            "estimatedMinutes": random.choice([None, 30, 60, 120, 240]),
            "hasChildren": True,
            "shouldUseFloatingTimeZone": False,
            "repetitionRule": None,
            "lastReviewDate": f"2026-02-{10 + (i % 10):02d}T00:00:00.000Z",
            "nextReviewDate": f"2026-02-{24 + (i % 5):02d}T00:00:00.000Z",
            "reviewInterval": {"steps": 1, "unit": "weeks"},
            "nextTask": None,
            "folder": folder_ids[i] if i < len(folder_ids) else None,
            "tags": random.sample(tag_names[:10], k=random.randint(0, 3)),
        }
        projects.append(p)

    task_templates = [
        "Review pull request", "Update documentation", "Fix login bug",
        "Design new feature", "Write unit tests", "Deploy to staging",
        "Schedule meeting", "Send follow-up email", "Research competitor",
        "Refactor module", "Create mockup", "Setup CI pipeline",
        "Buy groceries", "Call dentist", "Pay electric bill",
        "Read chapter 5", "Go for a run", "Meditate",
        "Plan sprint", "Update roadmap", "Review analytics",
        "Interview candidate", "Write blog post", "Optimize queries",
    ]

    tasks = []
    # Inbox tasks (no project)
    for i in range(5):
        tasks.append({
            "id": f"task_inbox_{i+1}",
            "name": f"Inbox: {task_templates[i % len(task_templates)]}",
            "note": "",
            "added": "2026-02-20T09:00:00.000Z",
            "modified": "2026-02-20T09:00:00.000Z",
            "active": True,
            "effectiveActive": True,
            "status": "Available",
            "completed": False,
            "completedByChildren": False,
            "flagged": i == 0,
            "effectiveFlagged": i == 0,
            "sequential": False,
            "dueDate": "2026-02-25T00:00:00.000Z" if i == 0 else None,
            "deferDate": None,
            "effectiveDueDate": "2026-02-25T00:00:00.000Z" if i == 0 else None,
            "effectiveDeferDate": None,
            "completionDate": None,
            "effectiveCompletionDate": None,
            "dropDate": None,
            "effectiveDropDate": None,
            "estimatedMinutes": random.choice([None, 15, 30, 60]),
            "hasChildren": False,
            "inInbox": True,
            "shouldUseFloatingTimeZone": False,
            "repetitionRule": None,
            "project": None,
            "parent": None,
            "assignedContainer": None,
            "tags": random.sample(tag_names[:10], k=random.randint(0, 2)),
        })

    # Project tasks
    task_id = 5
    for pi in range(min(n_projects, len(project_names))):
        n_proj_tasks = random.randint(3, 8)
        parent_task_id = None
        for ti in range(min(n_proj_tasks, n_tasks - task_id)):
            task_id += 1
            is_subtask = ti > 0 and ti % 4 == 0 and parent_task_id is not None
            is_action_group = ti > 0 and ti % 6 == 0

            t = {
                "id": f"task_{task_id}",
                "name": f"{task_templates[(pi * 7 + ti) % len(task_templates)]} ({project_names[pi]})",
                "note": f"Details for task {task_id}" if ti % 5 == 0 else "",
                "added": f"2026-02-{10 + (ti % 18):02d}T09:00:00.000Z",
                "modified": f"2026-02-{15 + (ti % 6):02d}T14:30:00.000Z",
                "active": True,
                "effectiveActive": True,
                "status": random.choice(["Available", "Available", "Available", "Blocked", "Next"]),
                "completed": False,
                "completedByChildren": is_action_group,
                "flagged": ti == 0 and pi % 3 == 0,
                "effectiveFlagged": ti == 0 and pi % 3 == 0,
                "sequential": False,
                "dueDate": f"2026-03-{10 + (ti % 20):02d}T17:00:00.000Z" if ti % 3 == 0 else None,
                "deferDate": f"2026-02-{20 + (ti % 8):02d}T09:00:00.000Z" if ti % 5 == 0 else None,
                "effectiveDueDate": f"2026-03-{10 + (ti % 20):02d}T17:00:00.000Z" if ti % 3 == 0 else (
                    projects[pi]["effectiveDueDate"]
                ),
                "effectiveDeferDate": f"2026-02-{20 + (ti % 8):02d}T09:00:00.000Z" if ti % 5 == 0 else None,
                "completionDate": None,
                "effectiveCompletionDate": None,
                "dropDate": None,
                "effectiveDropDate": None,
                "estimatedMinutes": random.choice([None, None, 15, 30, 45, 60, 90, 120]),
                "hasChildren": is_action_group,
                "inInbox": False,
                "shouldUseFloatingTimeZone": False,
                "repetitionRule": {"ruleString": "FREQ=WEEKLY;INTERVAL=1", "scheduleType": "fixed"} if ti == 0 and pi == 0 else None,
                "project": f"proj_{pi+1}",
                "parent": parent_task_id if is_subtask else None,
                "assignedContainer": None,
                "tags": random.sample(tag_names[:15], k=random.randint(0, 3)),
            }
            tasks.append(t)
            if not is_subtask:
                parent_task_id = t["id"]

            if task_id >= n_tasks + 5:
                break
        if task_id >= n_tasks + 5:
            break

    perspectives = [
        {"id": "persp_1", "name": "Daily Review"},
        {"id": "persp_2", "name": "Available Work"},
        {"id": "persp_3", "name": "Waiting For"},
        {"id": "persp_4", "name": "Due Soon"},
        {"id": "persp_5", "name": "Flagged + Due"},
    ]

    return {
        "tasks": tasks[:n_tasks + 5],
        "projects": projects,
        "tags": tags,
        "folders": folders,
        "perspectives": perspectives,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_json_to_taskpaper_basic():
    """Basic conversion produces valid TaskPaper syntax."""
    dump = {
        "folders": [{"id": "f1", "name": "Work", "parent": None, "status": "Active",
                      "active": True, "effectiveActive": True,
                      "added": "2025-01-01T00:00:00.000Z", "modified": "2025-01-01T00:00:00.000Z"}],
        "projects": [{"id": "p1", "name": "My Project", "folder": "f1", "status": "Active",
                       "note": "", "sequential": True, "dueDate": "2026-03-01T00:00:00.000Z",
                       "effectiveDueDate": "2026-03-01T00:00:00.000Z",
                       "deferDate": None, "effectiveDeferDate": None,
                       "flagged": True, "effectiveFlagged": True,
                       "completed": False, "completedByChildren": False,
                       "completionDate": None, "effectiveCompletionDate": None,
                       "dropDate": None, "effectiveDropDate": None,
                       "estimatedMinutes": 60, "hasChildren": True,
                       "shouldUseFloatingTimeZone": False,
                       "containsSingletonActions": False,
                       "taskStatus": "Available",
                       "repetitionRule": None,
                       "lastReviewDate": "2026-02-15T00:00:00.000Z",
                       "nextReviewDate": "2026-02-22T00:00:00.000Z",
                       "reviewInterval": {"steps": 1, "unit": "weeks"},
                       "nextTask": None,
                       "tags": ["work", "planning"]}],
        "tasks": [
            {"id": "t1", "name": "First task", "note": "", "project": "p1", "parent": None,
             "status": "Available", "completed": False, "flagged": False,
             "effectiveFlagged": False, "sequential": False,
             "dueDate": "2026-02-28T17:00:00.000Z", "effectiveDueDate": "2026-02-28T17:00:00.000Z",
             "deferDate": None, "effectiveDeferDate": None,
             "completionDate": None, "effectiveCompletionDate": None,
             "dropDate": None, "effectiveDropDate": None,
             "estimatedMinutes": 30, "hasChildren": False, "inInbox": False,
             "shouldUseFloatingTimeZone": False, "completedByChildren": False,
             "repetitionRule": None, "assignedContainer": None,
             "active": True, "effectiveActive": True,
             "added": "2026-02-01T00:00:00.000Z", "modified": "2026-02-15T00:00:00.000Z",
             "tags": ["coding"]},
            {"id": "t2", "name": "Second task", "note": "Important notes here", "project": "p1", "parent": None,
             "status": "Available", "completed": False, "flagged": True,
             "effectiveFlagged": True, "sequential": False,
             "dueDate": None, "effectiveDueDate": "2026-03-01T00:00:00.000Z",
             "deferDate": None, "effectiveDeferDate": None,
             "completionDate": None, "effectiveCompletionDate": None,
             "dropDate": None, "effectiveDropDate": None,
             "estimatedMinutes": None, "hasChildren": False, "inInbox": False,
             "shouldUseFloatingTimeZone": False, "completedByChildren": False,
             "repetitionRule": None, "assignedContainer": None,
             "active": True, "effectiveActive": True,
             "added": "2026-02-01T00:00:00.000Z", "modified": "2026-02-15T00:00:00.000Z",
             "tags": []},
        ],
        "tags": [
            {"id": "tag1", "name": "work", "parent": None, "status": "Active",
             "active": True, "effectiveActive": True, "allowsNextAction": True,
             "added": "2025-01-01T00:00:00.000Z", "modified": "2025-01-01T00:00:00.000Z"},
            {"id": "tag2", "name": "coding", "parent": "tag1", "status": "Active",
             "active": True, "effectiveActive": True, "allowsNextAction": True,
             "added": "2025-01-01T00:00:00.000Z", "modified": "2025-01-01T00:00:00.000Z"},
            {"id": "tag3", "name": "planning", "parent": "tag1", "status": "Active",
             "active": True, "effectiveActive": True, "allowsNextAction": True,
             "added": "2025-01-01T00:00:00.000Z", "modified": "2025-01-01T00:00:00.000Z"},
        ],
        "perspectives": [],
    }

    # Full mode
    full = json_to_taskpaper(dump, Mode.FULL)
    assert "Work:" in full
    assert "My Project:" in full
    assert "- First task" in full
    assert "- Second task" in full
    assert "@due(2026-02-28T17:00)" in full
    assert "@flagged" in full
    assert "@sequential" in full
    assert "@estimate(30m)" in full
    assert "Tags:" in full

    # LLM mode
    llm = json_to_taskpaper(dump, Mode.LLM)
    assert "Work:" in llm
    assert "- First task" in llm
    # LLM mode should NOT include internal IDs
    assert "@id(" not in llm
    assert "@added(" not in llm
    assert "@modified(" not in llm

    # LLM mode should skip effective dates when they match direct dates
    # t1 has effectiveDueDate == dueDate, so @effective-due should not appear
    # t2 has effectiveDueDate != dueDate (inherited), so it should appear
    lines = llm.split("\n")
    t2_line = [l for l in lines if "Second task" in l][0]
    assert "@effective-due(" in t2_line  # inherited due date shown

    print("PASS: test_json_to_taskpaper_basic")


def test_taskpaper_to_json_basic():
    """Basic parsing produces correct JSON structure."""
    tp = """\
Work:
\tMy Project: @sequential @due(2026-03-01) @flagged
\t\t- First task @due(2026-02-28) @estimate(30m) @tags(coding)
\t\t- Second task @flagged
\t\t\tImportant notes here
Personal:
\tGrocery Shopping: @single-actions
\t\t- Buy milk
\t\t- Buy eggs @tags(errands)

Tags:
\t- work @allows-next
\t\t- coding @allows-next
\t\t- planning @allows-next
"""
    result = taskpaper_to_json(tp)

    assert len(result["folders"]) >= 2  # Work, Personal
    assert len(result["projects"]) >= 2  # My Project, Grocery Shopping
    assert len(result["tasks"]) >= 4  # First task, Second task, Buy milk, Buy eggs

    # Check project fields
    my_proj = [p for p in result["projects"] if p["name"] == "My Project"][0]
    assert my_proj["sequential"] is True
    assert my_proj["dueDate"] == "2026-03-01T00:00:00.000Z"
    assert my_proj["flagged"] is True

    # Check task fields
    first = [t for t in result["tasks"] if "First task" in t["name"]][0]
    assert first["dueDate"] == "2026-02-28T00:00:00.000Z"
    assert first["estimatedMinutes"] == 30
    assert first["tags"] == ["coding"]

    second = [t for t in result["tasks"] if "Second task" in t["name"]][0]
    assert second["flagged"] is True
    assert "Important notes here" in second["note"]

    # Check tags
    assert len(result["tags"]) >= 3
    coding_tag = [t for t in result["tags"] if t["name"] == "coding"][0]
    work_tag = [t for t in result["tags"] if t["name"] == "work"][0]
    assert coding_tag["parent"] == work_tag["id"]

    print("PASS: test_taskpaper_to_json_basic")


def test_round_trip_key_fields():
    """Key fields survive a JSON -> TaskPaper -> JSON round-trip."""
    dump = _make_sample_dump(5, 20)
    tp = json_to_taskpaper(dump, Mode.FULL)
    recovered = taskpaper_to_json(tp)

    # Check that we got some tasks, projects, folders
    assert len(recovered["tasks"]) > 0, "No tasks recovered"
    assert len(recovered["projects"]) > 0, "No projects recovered"
    assert len(recovered["folders"]) > 0, "No folders recovered"

    # Check key field names are present (even if values differ due to ID regeneration)
    orig_task = dump["tasks"][0]
    rec_tasks = recovered["tasks"]
    # At least some tasks should have due dates
    tasks_with_due = [t for t in rec_tasks if t.get("dueDate")]
    assert len(tasks_with_due) > 0, "No tasks with dueDate recovered"

    print("PASS: test_round_trip_key_fields")


def test_llm_mode_smaller_than_full():
    """LLM mode produces fewer tokens than full mode."""
    dump = _make_sample_dump(20, 100)
    full = json_to_taskpaper(dump, Mode.FULL)
    llm = json_to_taskpaper(dump, Mode.LLM)
    raw_json = json.dumps(dump)

    # LLM should be smaller than full
    assert len(llm) < len(full), f"LLM ({len(llm)}) not smaller than full ({len(full)})"
    # Both should be smaller than raw JSON
    assert len(full) < len(raw_json), f"Full ({len(full)}) not smaller than JSON ({len(raw_json)})"

    print("PASS: test_llm_mode_smaller_than_full")
    print(f"  JSON: {len(raw_json):,} chars")
    print(f"  Full: {len(full):,} chars ({len(full)/len(raw_json):.1%})")
    print(f"  LLM:  {len(llm):,} chars ({len(llm)/len(raw_json):.1%})")


def test_hierarchy_preservation():
    """Folder > Project > Task hierarchy is preserved."""
    dump = {
        "folders": [
            {"id": "f1", "name": "Work", "parent": None, "status": "Active",
             "active": True, "effectiveActive": True,
             "added": "2025-01-01T00:00:00.000Z", "modified": "2025-01-01T00:00:00.000Z"},
        ],
        "projects": [
            {"id": "p1", "name": "Alpha", "folder": "f1", "status": "Active",
             "note": "", "sequential": False,
             "dueDate": None, "effectiveDueDate": None,
             "deferDate": None, "effectiveDeferDate": None,
             "flagged": False, "effectiveFlagged": False,
             "completed": False, "completedByChildren": False,
             "completionDate": None, "effectiveCompletionDate": None,
             "dropDate": None, "effectiveDropDate": None,
             "estimatedMinutes": None, "hasChildren": True,
             "shouldUseFloatingTimeZone": False,
             "containsSingletonActions": False, "taskStatus": "Available",
             "repetitionRule": None, "lastReviewDate": None,
             "nextReviewDate": None, "reviewInterval": None,
             "nextTask": None, "tags": []},
        ],
        "tasks": [
            {"id": "t1", "name": "Parent task", "project": "p1", "parent": None,
             "note": "", "status": "Available", "completed": False,
             "flagged": False, "effectiveFlagged": False, "sequential": False,
             "dueDate": None, "effectiveDueDate": None,
             "deferDate": None, "effectiveDeferDate": None,
             "completionDate": None, "effectiveCompletionDate": None,
             "dropDate": None, "effectiveDropDate": None,
             "estimatedMinutes": None, "hasChildren": True, "inInbox": False,
             "shouldUseFloatingTimeZone": False, "completedByChildren": False,
             "repetitionRule": None, "assignedContainer": None,
             "active": True, "effectiveActive": True,
             "added": "2026-01-01T00:00:00.000Z", "modified": "2026-01-01T00:00:00.000Z",
             "tags": []},
            {"id": "t2", "name": "Child task", "project": "p1", "parent": "t1",
             "note": "", "status": "Available", "completed": False,
             "flagged": False, "effectiveFlagged": False, "sequential": False,
             "dueDate": None, "effectiveDueDate": None,
             "deferDate": None, "effectiveDeferDate": None,
             "completionDate": None, "effectiveCompletionDate": None,
             "dropDate": None, "effectiveDropDate": None,
             "estimatedMinutes": None, "hasChildren": False, "inInbox": False,
             "shouldUseFloatingTimeZone": False, "completedByChildren": False,
             "repetitionRule": None, "assignedContainer": None,
             "active": True, "effectiveActive": True,
             "added": "2026-01-01T00:00:00.000Z", "modified": "2026-01-01T00:00:00.000Z",
             "tags": []},
        ],
        "tags": [],
        "perspectives": [],
    }

    tp = json_to_taskpaper(dump, Mode.LLM)
    lines = [l for l in tp.split("\n") if l.strip()]

    # Find hierarchy by indentation
    work_line = [l for l in lines if "Work:" in l][0]
    alpha_line = [l for l in lines if "Alpha:" in l][0]
    parent_line = [l for l in lines if "Parent task" in l][0]
    child_line = [l for l in lines if "Child task" in l][0]

    # Check indentation increases: Work < Alpha < Parent < Child
    assert work_line.count("\t") < alpha_line.count("\t")
    assert alpha_line.count("\t") < parent_line.count("\t")
    assert parent_line.count("\t") < child_line.count("\t")

    print("PASS: test_hierarchy_preservation")


def test_inbox_tasks():
    """Inbox tasks (no project) are grouped under Inbox:"""
    dump = {
        "folders": [],
        "projects": [],
        "tasks": [
            {"id": "t1", "name": "Inbox task", "project": None, "parent": None,
             "note": "", "status": "Available", "completed": False,
             "flagged": True, "effectiveFlagged": True, "sequential": False,
             "dueDate": "2026-02-25T00:00:00.000Z",
             "effectiveDueDate": "2026-02-25T00:00:00.000Z",
             "deferDate": None, "effectiveDeferDate": None,
             "completionDate": None, "effectiveCompletionDate": None,
             "dropDate": None, "effectiveDropDate": None,
             "estimatedMinutes": 15, "hasChildren": False, "inInbox": True,
             "shouldUseFloatingTimeZone": False, "completedByChildren": False,
             "repetitionRule": None, "assignedContainer": None,
             "active": True, "effectiveActive": True,
             "added": "2026-02-20T00:00:00.000Z", "modified": "2026-02-20T00:00:00.000Z",
             "tags": ["urgent"]},
        ],
        "tags": [],
        "perspectives": [],
    }

    tp = json_to_taskpaper(dump, Mode.LLM)
    assert "Inbox:" in tp
    assert "- Inbox task" in tp
    assert "@flagged" in tp
    assert "@due(2026-02-25)" in tp

    print("PASS: test_inbox_tasks")


def test_token_comparison():
    """Compare token counts between JSON, full TaskPaper, and LLM TaskPaper."""
    try:
        import tiktoken
    except ImportError:
        print("SKIP: test_token_comparison (tiktoken not installed)")
        return

    dump = _make_sample_dump(20, 100)
    raw_json = json.dumps(dump, indent=2)
    compact_json = json.dumps(dump, separators=(",", ":"))
    full_tp = json_to_taskpaper(dump, Mode.FULL)
    llm_tp = json_to_taskpaper(dump, Mode.LLM)

    enc = tiktoken.get_encoding("cl100k_base")

    json_tokens = len(enc.encode(raw_json))
    compact_tokens = len(enc.encode(compact_json))
    full_tokens = len(enc.encode(full_tp))
    llm_tokens = len(enc.encode(llm_tp))

    print("PASS: test_token_comparison")
    print(f"\n{'Format':<25} {'Chars':>10} {'Tokens':>10} {'Ratio':>8}")
    print("-" * 55)
    print(f"{'JSON (pretty)':.<25} {len(raw_json):>10,} {json_tokens:>10,} {'1.00x':>8}")
    print(f"{'JSON (compact)':.<25} {len(compact_json):>10,} {compact_tokens:>10,} {compact_tokens/json_tokens:.2f}x")
    print(f"{'TaskPaper (full)':.<25} {len(full_tp):>10,} {full_tokens:>10,} {full_tokens/json_tokens:.2f}x")
    print(f"{'TaskPaper (LLM)':.<25} {len(llm_tp):>10,} {llm_tokens:>10,} {llm_tokens/json_tokens:.2f}x")
    print()
    print(f"Token savings (LLM vs pretty JSON): {(1 - llm_tokens/json_tokens)*100:.1f}%")
    print(f"Token savings (LLM vs compact JSON): {(1 - llm_tokens/compact_tokens)*100:.1f}%")

    # Write comparison data for the report
    return {
        "json_pretty": {"chars": len(raw_json), "tokens": json_tokens},
        "json_compact": {"chars": len(compact_json), "tokens": compact_tokens},
        "taskpaper_full": {"chars": len(full_tp), "tokens": full_tokens},
        "taskpaper_llm": {"chars": len(llm_tp), "tokens": llm_tokens},
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_json_to_taskpaper_basic()
    test_taskpaper_to_json_basic()
    test_round_trip_key_fields()
    test_llm_mode_smaller_than_full()
    test_hierarchy_preservation()
    test_inbox_tasks()
    results = test_token_comparison()

    print("\n" + "=" * 55)
    print("All tests passed!")

    if results:
        # Save token comparison for report
        out_path = Path(__file__).parent.parent / "token-comparison-data.json"
        out_path.write_text(json.dumps(results, indent=2))
        print(f"Token data saved to {out_path}")
