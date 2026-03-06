// 21 — [WRITE] Task-Level Write Operations
// ⚠️ WRITES TO OMNIFOCUS DATABASE
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Tests task-level write operations (distinct from project-level in Script 07):
// - Complete a task → status, active, effectiveActive
// - Un-complete → verify revert
// - Set deferDate to future → does taskStatus change to Blocked?
// - Clear deferDate → does it revert?
// - Drop a task → status, active
// - Un-drop attempt → can we recover?
// - Flag/unflag
//
// Self-cleaning: creates test data, runs tests, cleans up.
// If interrupted, run Script 08 to clean up "🧪 API Audit" entities.

(() => {
  let r = `=== 21: [WRITE] Task-Level Write Operations ===\n\n`;

  function resolveTaskStatus(t) {
    const s = t.taskStatus;
    if (s === Task.Status.Available) return "Available";
    if (s === Task.Status.Blocked) return "Blocked";
    if (s === Task.Status.Completed) return "Completed";
    if (s === Task.Status.Dropped) return "Dropped";
    if (s === Task.Status.DueSoon) return "DueSoon";
    if (s === Task.Status.Next) return "Next";
    if (s === Task.Status.Overdue) return "Overdue";
    return "UNKNOWN";
  }

  function snap(t) {
    return `status=${resolveTaskStatus(t)}, active=${t.active}, effActive=${t.effectiveActive}, completed=${t.completed}`;
  }

  // --- Setup ---
  r += `--- Setup ---\n`;
  let auditTag = null;
  const allTags = flattenedTags;
  for (let i = 0; i < allTags.length; i++) {
    if (allTags[i].name === "🧪 API Audit") { auditTag = allTags[i]; break; }
  }
  if (!auditTag) {
    auditTag = new Tag("🧪 API Audit");
    r += `Created tag: 🧪 API Audit\n`;
  } else {
    r += `Found existing tag: 🧪 API Audit\n`;
  }

  const project = new Project("🧪 API Audit Write Test");
  project.addTag(auditTag);

  const task1 = new Task("🧪 Task Write Test 1", project);
  task1.addTag(auditTag);
  const task2 = new Task("🧪 Task Write Test 2", project);
  task2.addTag(auditTag);
  const task3 = new Task("🧪 Task Write Test 3", project);
  task3.addTag(auditTag);

  r += `Created project + 3 tasks\n`;
  r += `  task1: ${snap(task1)}\n`;
  r += `  task2: ${snap(task2)}\n`;
  r += `  task3: ${snap(task3)}\n\n`;

  // --- Test 1: Complete a task ---
  r += `--- Test 1: Complete task1 ---\n`;
  r += `  Before: ${snap(task1)}\n`;
  task1.markComplete();
  r += `  After markComplete(): ${snap(task1)}\n`;
  r += `  completionDate: ${task1.completionDate}\n\n`;

  // --- Test 2: Un-complete ---
  r += `--- Test 2: Un-complete task1 ---\n`;
  task1.markIncomplete();
  r += `  After markIncomplete(): ${snap(task1)}\n`;
  r += `  completionDate: ${task1.completionDate}\n\n`;

  // --- Test 3: Set deferDate to future ---
  r += `--- Test 3: Set task2.deferDate to future ---\n`;
  r += `  Before: ${snap(task2)}\n`;
  const futureDefer = new Date();
  futureDefer.setDate(futureDefer.getDate() + 30);
  task2.deferDate = futureDefer;
  r += `  After deferDate=${futureDefer.toISOString().slice(0,10)}: ${snap(task2)}\n\n`;

  // --- Test 4: Clear deferDate ---
  r += `--- Test 4: Clear task2.deferDate ---\n`;
  task2.deferDate = null;
  r += `  After clearing: ${snap(task2)}\n\n`;

  // --- Test 5: Set dueDate to past (make Overdue) ---
  r += `--- Test 5: Set task2.dueDate to past ---\n`;
  r += `  Before: ${snap(task2)}\n`;
  const pastDue = new Date();
  pastDue.setDate(pastDue.getDate() - 3);
  task2.dueDate = pastDue;
  r += `  After dueDate=${pastDue.toISOString().slice(0,10)}: ${snap(task2)}\n`;
  r += `  (Expected: Overdue if task is available)\n\n`;

  // --- Test 6: Set deferDate to future on overdue task ---
  r += `--- Test 6: Set deferDate to future on overdue task ---\n`;
  r += `  Before: ${snap(task2)}\n`;
  task2.deferDate = futureDefer;
  r += `  After adding future defer: ${snap(task2)}\n`;
  r += `  (Key: does Overdue change to Blocked when deferred?)\n\n`;

  // Clear for next test
  task2.deferDate = null;
  task2.dueDate = null;

  // --- Test 7: Drop a task ---
  r += `--- Test 7: Drop task3 ---\n`;
  r += `  Before: ${snap(task3)}\n`;
  task3.drop(true);
  r += `  After drop(true): ${snap(task3)}\n`;
  r += `  dropDate: ${task3.dropDate}\n\n`;

  // --- Test 8: Un-drop attempt ---
  r += `--- Test 8: Attempt to un-drop task3 ---\n`;
  try {
    task3.markIncomplete();
    r += `  After markIncomplete(): ${snap(task3)}\n`;
    r += `  dropDate: ${task3.dropDate}\n`;
    r += `  (markIncomplete un-dropped the task)\n`;
  } catch(e) {
    r += `  markIncomplete() error: ${e.message}\n`;
    r += `  (Cannot un-drop via markIncomplete)\n`;
  }
  r += `\n`;

  // --- Test 9: Flag/unflag ---
  r += `--- Test 9: Flag task1 ---\n`;
  r += `  Before: flagged=${task1.flagged}, effFlagged=${task1.effectiveFlagged}\n`;
  task1.flagged = true;
  r += `  After flag: flagged=${task1.flagged}, effFlagged=${task1.effectiveFlagged}\n`;
  task1.flagged = false;
  r += `  After unflag: flagged=${task1.flagged}, effFlagged=${task1.effectiveFlagged}\n\n`;

  // --- Cleanup ---
  r += `--- Cleanup ---\n`;
  try {
    deleteObject(project);
    r += `  Project + tasks deleted ✅\n`;
  } catch(e) {
    r += `  Project delete error: ${e.message}\n`;
  }

  try {
    deleteObject(auditTag);
    r += `  Tag deleted ✅\n`;
  } catch(e) {
    r += `  Tag delete: ${e.message}\n`;
  }

  r += `\nDone.\n`;
  return r;
})();
