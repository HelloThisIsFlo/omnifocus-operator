// 07 — [WRITE] Modify and Verify
// ⚠️ WRITES TO OMNIFOCUS DATABASE (modifies test project created by Script 05)
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Tests property write proxying between p.* and p.task.*:
// 1. Set p.dueDate → check p.task.dueDate (project→task proxy?)
// 2. Clear p.dueDate = null → check p.task.dueDate follows
// 3. Set p.task.flagged = true → check p.flagged (task→project proxy?)
// 4. Mark project complete → check active, effectiveActive, status, taskStatus
// 5. Un-complete project → verify everything reverts

(() => {
  let r = `=== 07: [WRITE] Modify and Verify ===\n\n`;

  // Find test project
  const allProjects = flattenedProjects;
  let project = null;
  for (let i = 0; i < allProjects.length; i++) {
    if (allProjects[i].name === "🧪 API Audit Test Project") {
      project = allProjects[i];
      break;
    }
  }

  if (!project) {
    return r + `ERROR: Project "🧪 API Audit Test Project" not found. Run Script 05 first.\n`;
  }

  const p = project;
  const t = p.task;

  function matchProjectStatus(val) {
    if (val === null || val === undefined) return "null/undefined";
    try { if (val === Project.Status.Active) return "Active"; } catch(e) {}
    try { if (val === Project.Status.Done) return "Done"; } catch(e) {}
    try { if (val === Project.Status.Dropped) return "Dropped"; } catch(e) {}
    try { if (val === Project.Status.OnHold) return "OnHold"; } catch(e) {}
    return "UNKNOWN";
  }

  function matchTaskStatus(val) {
    if (val === null || val === undefined) return "null/undefined";
    try { if (val === Task.Status.Available) return "Available"; } catch(e) {}
    try { if (val === Task.Status.Blocked) return "Blocked"; } catch(e) {}
    try { if (val === Task.Status.Completed) return "Completed"; } catch(e) {}
    try { if (val === Task.Status.Dropped) return "Dropped"; } catch(e) {}
    try { if (val === Task.Status.DueSoon) return "DueSoon"; } catch(e) {}
    try { if (val === Task.Status.Next) return "Next"; } catch(e) {}
    try { if (val === Task.Status.Overdue) return "Overdue"; } catch(e) {}
    return "UNKNOWN";
  }

  function fmt(v) {
    if (v === undefined) return "undefined";
    if (v === null) return "null";
    if (v instanceof Date) return v.toISOString();
    return String(v);
  }

  function snapshot() {
    return {
      pDueDate: fmt(p.dueDate),
      tDueDate: fmt(t.dueDate),
      pFlagged: p.flagged,
      tFlagged: t.flagged,
      pEffFlagged: p.effectiveFlagged,
      tEffFlagged: t.effectiveFlagged,
      pCompleted: p.completed,
      tCompleted: t.completed,
      tActive: t.active,
      tEffActive: t.effectiveActive,
      pStatus: matchProjectStatus(p.status),
      tStatus: matchTaskStatus(t.taskStatus),
    };
  }

  function logSnapshot(label, s) {
    let out = `  [${label}]\n`;
    out += `    p.dueDate:          ${s.pDueDate}\n`;
    out += `    t.dueDate:          ${s.tDueDate}\n`;
    out += `    p.flagged:          ${s.pFlagged}\n`;
    out += `    t.flagged:          ${s.tFlagged}\n`;
    out += `    p.effectiveFlagged: ${s.pEffFlagged}\n`;
    out += `    t.effectiveFlagged: ${s.tEffFlagged}\n`;
    out += `    p.completed:        ${s.pCompleted}\n`;
    out += `    t.completed:        ${s.tCompleted}\n`;
    out += `    t.active:           ${s.tActive}\n`;
    out += `    t.effectiveActive:  ${s.tEffActive}\n`;
    out += `    p.status:           ${s.pStatus}\n`;
    out += `    t.taskStatus:       ${s.tStatus}\n`;
    return out;
  }

  // --- Baseline ---
  r += `--- Baseline ---\n`;
  r += logSnapshot("Before any changes", snapshot());

  // --- Test 1: Set p.dueDate → check p.task.dueDate ---
  r += `\n--- Test 1: Set p.dueDate → check t.dueDate ---\n`;
  const newDue = new Date(2026, 5, 15, 12, 0, 0);  // June 15, 2026 noon
  p.dueDate = newDue;
  r += `  Set p.dueDate = ${newDue.toISOString()}\n`;
  r += `  p.dueDate after:   ${fmt(p.dueDate)}\n`;
  r += `  t.dueDate after:   ${fmt(t.dueDate)}\n`;
  const dueDatesMatch = p.dueDate instanceof Date && t.dueDate instanceof Date &&
    p.dueDate.getTime() === t.dueDate.getTime();
  r += `  ➜ Proxied p→t: ${dueDatesMatch ? "YES ✅" : "NO ⚠️"}\n`;

  // --- Test 2: Clear p.dueDate = null → check t.dueDate ---
  r += `\n--- Test 2: Clear p.dueDate = null → check t.dueDate ---\n`;
  p.dueDate = null;
  r += `  Set p.dueDate = null\n`;
  r += `  p.dueDate after:   ${fmt(p.dueDate)}\n`;
  r += `  t.dueDate after:   ${fmt(t.dueDate)}\n`;
  const bothCleared = (p.dueDate === null || p.dueDate === undefined) &&
    (t.dueDate === null || t.dueDate === undefined);
  r += `  ➜ Clear proxied p→t: ${bothCleared ? "YES ✅" : "NO ⚠️"}\n`;

  // Restore due date
  p.dueDate = newDue;

  // --- Test 3: Set t.flagged = true → check p.flagged ---
  r += `\n--- Test 3: Set t.flagged = true → check p.flagged ---\n`;
  r += `  Before: p.flagged=${p.flagged}, t.flagged=${t.flagged}\n`;
  t.flagged = true;
  r += `  Set t.flagged = true\n`;
  r += `  p.flagged after:   ${p.flagged}\n`;
  r += `  t.flagged after:   ${t.flagged}\n`;
  r += `  ➜ Proxied t→p: ${p.flagged === true ? "YES ✅" : "NO ⚠️"}\n`;

  // Reset flagged
  t.flagged = false;

  // --- Test 4: Mark project complete ---
  r += `\n--- Test 4: Mark project complete ---\n`;
  r += logSnapshot("Before completion", snapshot());
  p.markComplete();
  r += logSnapshot("After p.markComplete()", snapshot());

  // --- Test 5: Un-complete project ---
  r += `\n--- Test 5: Un-complete project ---\n`;
  p.markIncomplete();
  r += logSnapshot("After p.markIncomplete()", snapshot());

  // --- Test 6: Set p.status to OnHold ---
  r += `\n--- Test 6: Set p.status to OnHold ---\n`;
  try {
    p.status = Project.Status.OnHold;
    r += logSnapshot("After p.status = OnHold", snapshot());
  } catch(e) {
    r += `  ERROR setting OnHold: ${e.message}\n`;
  }

  // Revert to Active
  try {
    p.status = Project.Status.Active;
    r += `\n  (Reverted to Active)\n`;
    r += logSnapshot("After revert to Active", snapshot());
  } catch(e) {
    r += `  ERROR reverting to Active: ${e.message}\n`;
  }

  r += `\n--- Complete ---\n`;
  r += `Test project left in Active state with dueDate restored.\n`;

  return r;
})();
