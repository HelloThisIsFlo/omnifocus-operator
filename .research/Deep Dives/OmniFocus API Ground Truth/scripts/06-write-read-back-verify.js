// 06 — Write Read-Back Verify
// READ-ONLY (reads data created by Script 05)
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Finds ALL projects tagged "API Audit". For each, reads properties from
// p.* vs p.task.*, reports child tasks with full field dump.
// Verifies controlled data from the comprehensive Script 05.

(() => {
  let r = `=== 06: Write Read-Back Verify ===\n\n`;

  const TAG_NAME = "API Audit";

  // --- Status helpers ---
  function projStatus(val) {
    if (val === null || val === undefined) return "null";
    if (val === Project.Status.Active) return "Active";
    if (val === Project.Status.Done) return "Done";
    if (val === Project.Status.Dropped) return "Dropped";
    if (val === Project.Status.OnHold) return "OnHold";
    return "UNKNOWN";
  }
  function taskStatus(val) {
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
    if (typeof v === "boolean") return String(v);
    if (typeof v === "number") return String(v);
    if (typeof v === "string") return `"${v.substring(0, 80)}"`;
    return String(v);
  }

  // Find audit tag
  let auditTag = null;
  for (const tg of flattenedTags) {
    if (tg.name === TAG_NAME) { auditTag = tg; break; }
  }
  if (!auditTag) {
    return r + `ERROR: Tag "${TAG_NAME}" not found. Run Script 05 first.\n`;
  }
  r += `Found tag: "${auditTag.name}" (id: ${auditTag.id.primaryKey})\n\n`;

  // Find all audit projects
  const auditProjects = [];
  for (const p of flattenedProjects) {
    if (p.tags.some(tg => tg.id.primaryKey === auditTag.id.primaryKey)) {
      auditProjects.push(p);
    }
  }
  r += `Found ${auditProjects.length} audit projects.\n\n`;

  if (auditProjects.length === 0) {
    return r + `ERROR: No projects tagged "${TAG_NAME}". Run Script 05 first.\n`;
  }

  // --- For each project ---
  for (const p of auditProjects) {
    const t = p.task;
    r += `${"=".repeat(60)}\n`;
    r += `Project: "${p.name}"\n`;
    r += `${"=".repeat(60)}\n\n`;

    // Identity
    r += `--- Identity ---\n`;
    r += `  p.id: ${p.id.primaryKey}  t.id: ${t.id.primaryKey}  match: ${p.id.primaryKey === t.id.primaryKey}\n\n`;

    // Task-only fields
    r += `--- Task-Only Fields ---\n`;
    for (const f of ["added", "modified", "active", "effectiveActive"]) {
      r += `  ${f}: p=${fmt(p[f])}, t=${fmt(t[f])}\n`;
    }

    // Status
    r += `\n--- Status ---\n`;
    r += `  p.status: ${projStatus(p.status)}  |  t.taskStatus: ${taskStatus(t.taskStatus)}\n`;
    r += `  p.completed: ${p.completed}  |  t.completed: ${t.completed}\n`;

    // Key shared fields (abbreviated — just flag divergences)
    r += `\n--- Shared Fields (divergences only) ---\n`;
    const sharedFields = [
      "name", "note", "completed", "completedByChildren",
      "flagged", "effectiveFlagged", "sequential",
      "dueDate", "deferDate", "completionDate",
      "effectiveDueDate", "effectiveDeferDate", "effectiveCompletedDate",
      "plannedDate", "effectivePlannedDate", "dropDate", "effectiveDropDate",
      "estimatedMinutes", "hasChildren", "shouldUseFloatingTimeZone"
    ];
    let divergences = 0;
    for (const f of sharedFields) {
      const pv = p[f];
      const tv = t[f];
      const match = (pv instanceof Date && tv instanceof Date) ?
        pv.getTime() === tv.getTime() : pv === tv;
      if (!match) {
        divergences++;
        r += `  DIVERGE ${f}: p=${fmt(pv)}, t=${fmt(tv)}\n`;
      }
    }
    if (divergences === 0) r += `  ZERO divergences on all ${sharedFields.length} fields\n`;

    // Project-specific
    r += `\n--- Project-Specific ---\n`;
    r += `  sequential: ${p.sequential}  completedByChildren: ${p.completedByChildren}\n`;
    r += `  containsSingletonActions: ${p.containsSingletonActions}\n`;
    const ri = p.reviewInterval;
    r += `  reviewInterval: ${ri ? `${ri.steps}:${ri.unit}` : "null"}\n`;
    r += `  nextTask: ${p.nextTask ? p.nextTask.name : "null"}\n`;
    r += `  parentFolder: ${p.parentFolder ? p.parentFolder.name : "null"}\n`;
    r += `  tags: [${p.tags.map(x => x.name).join(", ")}]\n`;
    r += `  inInbox: ${t.inInbox}\n`;

    // Child tasks (recursive)
    r += `\n--- Child Tasks ---\n`;
    const reportChild = (ct, indent) => {
      const pad = " ".repeat(indent);
      r += `${pad}${ct.name}\n`;
      r += `${pad}  id=${ct.id.primaryKey} status=${taskStatus(ct.taskStatus)} active=${ct.active} effActive=${ct.effectiveActive}\n`;
      r += `${pad}  flagged=${ct.flagged} effFlagged=${ct.effectiveFlagged} completed=${ct.completed} inInbox=${ct.inInbox}\n`;
      r += `${pad}  dueDate=${fmt(ct.dueDate)} effDueDate=${fmt(ct.effectiveDueDate)}\n`;
      r += `${pad}  deferDate=${fmt(ct.deferDate)} effDeferDate=${fmt(ct.effectiveDeferDate)}\n`;
      r += `${pad}  completionDate=${fmt(ct.completionDate)} dropDate=${fmt(ct.dropDate)}\n`;
      r += `${pad}  estimatedMinutes=${fmt(ct.estimatedMinutes)} sequential=${ct.sequential} cbc=${ct.completedByChildren}\n`;
      r += `${pad}  note=${fmt(ct.note)}\n`;
      r += `${pad}  tags=[${ct.tags.map(x => x.name).join(", ")}]\n`;
      // Relationships
      let cp = "null"; try { cp = ct.containingProject ? ct.containingProject.name : "null"; } catch(e) { cp = "ERROR"; }
      let par = "null"; try { par = ct.parent ? ct.parent.name : "null"; } catch(e) { par = "ERROR"; }
      let ac = "null"; try { ac = ct.assignedContainer ? ct.assignedContainer.name : "null"; } catch(e) { ac = "ERROR"; }
      r += `${pad}  containingProject=${cp} parent=${par} assignedContainer=${ac}\n`;
      if (ct.hasChildren) {
        for (const child of ct.children) reportChild(child, indent + 4);
      }
    };
    for (const ct of t.children) reportChild(ct, 4);
    r += `\n`;
  }

  return r;
})();
