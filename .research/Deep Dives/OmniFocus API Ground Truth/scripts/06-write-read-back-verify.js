// 06 — Write Read-Back Verify
// READ-ONLY (reads data created by Script 05)
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Finds the test project by tag. Reads ALL properties from both p.* and p.task.*.
// Full side-by-side comparison on controlled data where we know exactly what was set.

(() => {
  let r = `=== 06: Write Read-Back Verify ===\n\n`;

  // Find the audit tag
  const allTags = flattenedTags;
  let auditTag = null;
  for (let i = 0; i < allTags.length; i++) {
    if (allTags[i].name === "🧪 API Audit") {
      auditTag = allTags[i];
      break;
    }
  }

  if (!auditTag) {
    return r + `ERROR: Tag "🧪 API Audit" not found. Run Script 05 first.\n`;
  }
  r += `Found tag: "${auditTag.name}" (id: ${auditTag.id.primaryKey})\n\n`;

  // Find the test project
  const allProjects = flattenedProjects;
  let testProject = null;
  for (let i = 0; i < allProjects.length; i++) {
    if (allProjects[i].name === "🧪 API Audit Test Project") {
      testProject = allProjects[i];
      break;
    }
  }

  if (!testProject) {
    return r + `ERROR: Project "🧪 API Audit Test Project" not found. Run Script 05 first.\n`;
  }

  const p = testProject;
  const t = p.task;

  // Helper for status matching
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
    if (typeof v === "boolean") return String(v);
    if (typeof v === "number") return String(v);
    if (typeof v === "string") return `"${v.substring(0, 80)}"`;
    return String(v);
  }

  // --- Project properties: p.* vs p.task.* ---
  r += `=== Project: "${p.name}" ===\n\n`;

  // Identity
  r += `--- Identity ---\n`;
  r += `  p.id.primaryKey:     ${p.id.primaryKey}\n`;
  r += `  p.task.id.primaryKey:${t.id.primaryKey}\n`;
  r += `  IDs match:           ${p.id.primaryKey === t.id.primaryKey}\n\n`;

  // Task-only fields
  r += `--- Task-Only Fields (expected: undefined on p, defined on t) ---\n`;
  for (const f of ["added", "modified", "active", "effectiveActive"]) {
    const pv = p[f];
    const tv = t[f];
    r += `  ${f}:\n`;
    r += `    p: ${fmt(pv)}\n`;
    r += `    t: ${fmt(tv)}\n`;
  }

  // Status fields
  r += `\n--- Status ---\n`;
  r += `  p.status:       ${matchProjectStatus(p.status)} (raw type: ${typeof p.status})\n`;
  r += `  p.task.taskStatus: ${matchTaskStatus(t.taskStatus)} (raw type: ${typeof t.taskStatus})\n`;
  r += `  p.completed:    ${p.completed}\n`;
  r += `  p.task.completed:${t.completed}\n`;

  // Shared fields - side by side
  r += `\n--- Shared Fields (p.* vs p.task.*) ---\n`;
  const sharedFields = [
    "name", "note", "completed", "completedByChildren",
    "flagged", "effectiveFlagged", "sequential",
    "dueDate", "deferDate", "completionDate",
    "effectiveDueDate", "effectiveDeferDate", "effectiveCompletedDate",
    "plannedDate", "effectivePlannedDate", "dropDate", "effectiveDropDate",
    "estimatedMinutes", "hasChildren",
    "shouldUseFloatingTimeZone"
  ];

  for (const f of sharedFields) {
    const pv = p[f];
    const tv = t[f];
    const match = (pv instanceof Date && tv instanceof Date) ?
      pv.getTime() === tv.getTime() :
      pv === tv;
    const flag = match ? "✅" : "⚠️";
    r += `  ${flag} ${f}:\n`;
    r += `      p: ${fmt(pv)}\n`;
    r += `      t: ${fmt(tv)}\n`;
  }

  // Project-specific fields
  r += `\n--- Project-Specific Fields ---\n`;
  r += `  containsSingletonActions: ${p.containsSingletonActions}\n`;
  r += `  lastReviewDate: ${fmt(p.lastReviewDate)}\n`;
  r += `  nextReviewDate: ${fmt(p.nextReviewDate)}\n`;
  const riVal = p.reviewInterval;
  r += `  reviewInterval: ${riVal ? `steps=${riVal.steps}, unit=${riVal.unit}` : "null"}\n`;
  try {
    r += `  nextTask: ${p.nextTask ? p.nextTask.name : "null"}\n`;
  } catch(e) {
    r += `  nextTask: ERROR (${e.message})\n`;
  }
  r += `  parentFolder: ${p.parentFolder ? p.parentFolder.name : "null"}\n`;

  // Tags
  r += `\n--- Tags ---\n`;
  const pTags = p.tags;
  const tTags = t.tags;
  r += `  p.tags: [${pTags.map(x => x.name).join(", ")}] (${pTags.length})\n`;
  r += `  t.tags: [${tTags.map(x => x.name).join(", ")}] (${tTags.length})\n`;

  // inInbox on task
  r += `\n--- inInbox ---\n`;
  r += `  p.task.inInbox: ${t.inInbox}\n`;

  // --- Child tasks ---
  r += `\n\n=== Child Tasks ===\n`;
  const childTasks = t.tasks;
  r += `Number of child tasks: ${childTasks.length}\n\n`;

  for (let i = 0; i < childTasks.length; i++) {
    const ct = childTasks[i];
    r += `--- Task: "${ct.name}" ---\n`;
    r += `  id: ${ct.id.primaryKey}\n`;
    r += `  added: ${fmt(ct.added)}\n`;
    r += `  modified: ${fmt(ct.modified)}\n`;
    r += `  active: ${ct.active}\n`;
    r += `  effectiveActive: ${ct.effectiveActive}\n`;
    r += `  taskStatus: ${matchTaskStatus(ct.taskStatus)}\n`;
    r += `  inInbox: ${ct.inInbox}\n`;
    r += `  flagged: ${ct.flagged}\n`;
    r += `  effectiveFlagged: ${ct.effectiveFlagged}\n`;
    r += `  dueDate: ${fmt(ct.dueDate)}\n`;
    r += `  deferDate: ${fmt(ct.deferDate)}\n`;
    r += `  note: ${fmt(ct.note)}\n`;
    r += `  tags: [${ct.tags.map(x => x.name).join(", ")}]\n`;

    // Relationships
    try {
      r += `  project: ${ct.project ? ct.project.name : "null"}\n`;
    } catch(e) {
      r += `  project: ERROR (${e.message})\n`;
    }
    try {
      r += `  containingProject: ${ct.containingProject ? ct.containingProject.name : "null"}\n`;
    } catch(e) {
      r += `  containingProject: ERROR (${e.message})\n`;
    }
    try {
      r += `  parent: ${ct.parent ? ct.parent.name : "null"}\n`;
    } catch(e) {
      r += `  parent: ERROR (${e.message})\n`;
    }
    try {
      r += `  assignedContainer: ${ct.assignedContainer ? ct.assignedContainer.name : "null"}\n`;
    } catch(e) {
      r += `  assignedContainer: ERROR (${e.message})\n`;
    }
    r += `\n`;
  }

  return r;
})();
