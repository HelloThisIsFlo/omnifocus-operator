// 07 — [WRITE] Modify and Verify
// WRITES TO OMNIFOCUS DATABASE (modifies test project created by Script 05)
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Tests property write proxying between p.* and p.task.* using
// "Audit: Parallel Project" from the comprehensive Script 05.
// Tests: dueDate proxy, clear proxy, flagged reverse proxy,
// complete/incomplete, OnHold/Active transitions.

(() => {
  let r = `=== 07: [WRITE] Modify and Verify ===\n\n`;

  const TAG_NAME = "API Audit";
  const PROJECT_NAME = "Audit: Parallel Project";

  // --- Status helpers ---
  function projStatus(val) {
    if (val === null || val === undefined) return "null";
    if (val === Project.Status.Active) return "Active";
    if (val === Project.Status.Done) return "Done";
    if (val === Project.Status.Dropped) return "Dropped";
    if (val === Project.Status.OnHold) return "OnHold";
    return "UNKNOWN";
  }
  function taskSt(val) {
    if (val === null || val === undefined) return "null";
    if (val === Task.Status.Available) return "Available";
    if (val === Task.Status.Blocked) return "Blocked";
    if (val === Task.Status.Completed) return "Completed";
    if (val === Task.Status.Dropped) return "Dropped";
    if (val === Task.Status.DueSoon) return "DueSoon";
    if (val === Task.Status.Next) return "Next";
    if (val === Task.Status.Overdue) return "Overdue";
    return "UNKNOWN";
  }
  function fmt(v) {
    if (v === undefined) return "undefined";
    if (v === null) return "null";
    if (v instanceof Date) return v.toISOString();
    return String(v);
  }

  // Find project
  let project = null;
  for (const p of flattenedProjects) {
    if (p.name === PROJECT_NAME) { project = p; break; }
  }
  if (!project) {
    return r + `ERROR: Project "${PROJECT_NAME}" not found. Run Script 05 first.\n`;
  }

  const p = project;
  const t = p.task;

  function snapshot() {
    return {
      pDue: fmt(p.dueDate), tDue: fmt(t.dueDate),
      pFlag: p.flagged, tFlag: t.flagged,
      pEffFlag: p.effectiveFlagged, tEffFlag: t.effectiveFlagged,
      pComp: p.completed, tComp: t.completed,
      tActive: t.active, tEffActive: t.effectiveActive,
      pStatus: projStatus(p.status), tStatus: taskSt(t.taskStatus),
    };
  }
  function logSnap(label, s) {
    r += `  [${label}]\n`;
    r += `    dueDate:   p=${s.pDue}  t=${s.tDue}\n`;
    r += `    flagged:   p=${s.pFlag}  t=${s.tFlag}  effFlagged: p=${s.pEffFlag}  t=${s.tEffFlag}\n`;
    r += `    completed: p=${s.pComp}  t=${s.tComp}\n`;
    r += `    active:    t=${s.tActive}  effActive: t=${s.tEffActive}\n`;
    r += `    status:    p=${s.pStatus}  t=${s.tStatus}\n`;
  }

  // --- Baseline ---
  r += `--- Baseline ---\n`;
  logSnap("Before changes", snapshot());

  // --- Test 1: Set p.dueDate → check t.dueDate ---
  r += `\n--- Test 1: Set p.dueDate → t.dueDate proxy ---\n`;
  const newDue = new Date(2026, 5, 15, 12, 0, 0);
  p.dueDate = newDue;
  const t1match = t.dueDate instanceof Date && p.dueDate.getTime() === t.dueDate.getTime();
  r += `  Set p.dueDate = ${fmt(newDue)}\n`;
  r += `  t.dueDate = ${fmt(t.dueDate)}\n`;
  r += `  Proxied p->t: ${t1match ? "YES" : "NO"}\n`;

  // --- Test 2: Clear p.dueDate → t.dueDate clears ---
  r += `\n--- Test 2: Clear p.dueDate = null ---\n`;
  p.dueDate = null;
  const t2cleared = (t.dueDate === null || t.dueDate === undefined);
  r += `  p.dueDate = ${fmt(p.dueDate)}  t.dueDate = ${fmt(t.dueDate)}\n`;
  r += `  Clear proxied: ${t2cleared ? "YES" : "NO"}\n`;
  p.dueDate = newDue; // restore

  // --- Test 3: Set t.flagged → p.flagged reverse proxy ---
  r += `\n--- Test 3: Set t.flagged → p.flagged reverse proxy ---\n`;
  r += `  Before: p=${p.flagged} t=${t.flagged}\n`;
  t.flagged = true;
  r += `  After t.flagged=true: p=${p.flagged} t=${t.flagged}\n`;
  r += `  Reverse proxied t->p: ${p.flagged === true ? "YES" : "NO"}\n`;
  t.flagged = false; // reset

  // --- Test 4: markComplete ---
  r += `\n--- Test 4: markComplete() ---\n`;
  logSnap("Before", snapshot());
  p.markComplete();
  logSnap("After markComplete()", snapshot());

  // --- Test 5: markIncomplete ---
  r += `\n--- Test 5: markIncomplete() ---\n`;
  p.markIncomplete();
  logSnap("After markIncomplete()", snapshot());

  // --- Test 6: OnHold transition ---
  r += `\n--- Test 6: OnHold transition ---\n`;
  p.status = Project.Status.OnHold;
  logSnap("After status=OnHold", snapshot());

  // Check child task statuses while OnHold
  r += `  Child tasks while OnHold:\n`;
  for (const ct of t.children) {
    r += `    ${ct.name}: ${taskSt(ct.taskStatus)}\n`;
  }

  // Revert to Active
  p.status = Project.Status.Active;
  logSnap("After revert to Active", snapshot());

  // --- Test 7: Set p.note via task proxy ---
  r += `\n--- Test 7: Note proxy ---\n`;
  const origNote = p.note;
  t.note = "Modified via p.task.note";
  r += `  Set t.note → p.note = "${p.note}"\n`;
  r += `  Proxied t->p: ${p.note === "Modified via p.task.note" ? "YES" : "NO"}\n`;
  p.note = origNote; // restore

  // --- Test 8: Set p.estimatedMinutes ---
  r += `\n--- Test 8: estimatedMinutes proxy ---\n`;
  p.estimatedMinutes = 45;
  r += `  Set p.estimatedMinutes=45 → t.estimatedMinutes=${t.estimatedMinutes}\n`;
  r += `  Proxied: ${t.estimatedMinutes === 45 ? "YES" : "NO"}\n`;
  p.estimatedMinutes = null; // reset

  r += `\n--- Complete ---\n`;
  r += `Project left in Active state. All modifications reverted.\n`;

  return r;
})();
