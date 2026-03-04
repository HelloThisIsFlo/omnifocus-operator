// 04 — Project Status Cross-Reference
// READ-ONLY — no modifications to OmniFocus data
//
// Maps the relationship between the three status systems on projects:
// 1. Project.Status (Active, OnHold, Done, Dropped)
// 2. Root task active/effectiveActive booleans
// 3. Root task Task.Status (Available, Blocked, Completed, Dropped, etc.)
//
// Answers: "When a project is OnHold, what are active and effectiveActive?"

(() => {
  const app = Application("OmniFocus");
  const doc = app.defaultDocument;
  const projects = doc.flattenedProjects();
  const total = projects.length;

  // === matching functions ===
  function matchProjectStatus(val) {
    if (val === null || val === undefined) return "null";
    try { if (val === Project.Status.Active) return "Active"; } catch(e) {}
    try { if (val === Project.Status.Done) return "Done"; } catch(e) {}
    try { if (val === Project.Status.Dropped) return "Dropped"; } catch(e) {}
    try { if (val === Project.Status.OnHold) return "OnHold"; } catch(e) {}
    return "UNKNOWN";
  }

  function matchTaskStatus(val) {
    if (val === null || val === undefined) return "null";
    try { if (val === Task.Status.Available) return "Available"; } catch(e) {}
    try { if (val === Task.Status.Blocked) return "Blocked"; } catch(e) {}
    try { if (val === Task.Status.Completed) return "Completed"; } catch(e) {}
    try { if (val === Task.Status.Dropped) return "Dropped"; } catch(e) {}
    try { if (val === Task.Status.DueSoon) return "DueSoon"; } catch(e) {}
    try { if (val === Task.Status.Next) return "Next"; } catch(e) {}
    try { if (val === Task.Status.Overdue) return "Overdue"; } catch(e) {}
    return "UNKNOWN";
  }

  // Group projects by Project.Status, then count distributions of task properties
  let groups = {};  // projStatus → { taskStatus → count }
  let activeGroups = {};     // projStatus → { "active=T,effActive=T" → count }
  let examples = {};  // projStatus → first 2 project names

  for (let i = 0; i < total; i++) {
    const p = projects[i];
    const t = p.task();

    const ps = matchProjectStatus(p.status());
    const ts = matchTaskStatus(t.status());
    const active = t.active();
    const effActive = t.effectiveActive();

    // Task status distribution per project status
    if (!groups[ps]) groups[ps] = {};
    groups[ps][ts] = (groups[ps][ts] || 0) + 1;

    // Active/effectiveActive distribution per project status
    const activeKey = `active=${active}, effActive=${effActive}`;
    if (!activeGroups[ps]) activeGroups[ps] = {};
    activeGroups[ps][activeKey] = (activeGroups[ps][activeKey] || 0) + 1;

    // Examples
    if (!examples[ps]) examples[ps] = [];
    if (examples[ps].length < 2) examples[ps].push(p.name());
  }

  // --- Report ---
  let r = `=== 04: Project Status Cross-Reference ===\n`;
  r += `Total projects: ${total}\n\n`;

  const statusOrder = ["Active", "OnHold", "Done", "Dropped", "UNKNOWN", "null"];

  for (const ps of statusOrder) {
    if (!groups[ps]) continue;

    const groupTotal = Object.values(groups[ps]).reduce((a, b) => a + b, 0);
    r += `=== Project.Status: ${ps} (${groupTotal} projects) ===\n`;

    if (examples[ps]) {
      r += `  Examples: ${examples[ps].map(n => `"${n}"`).join(", ")}\n`;
    }

    r += `  Task.Status distribution:\n`;
    for (const [ts, count] of Object.entries(groups[ps]).sort((a, b) => b[1] - a[1])) {
      r += `    ${ts}: ${count}\n`;
    }

    r += `  active/effectiveActive distribution:\n`;
    for (const [key, count] of Object.entries(activeGroups[ps]).sort((a, b) => b[1] - a[1])) {
      r += `    ${key}: ${count}\n`;
    }
    r += `\n`;
  }

  // Summary table
  r += `=== Summary: Project.Status → Root Task Behavior ===\n`;
  r += `  Active   → task.active=?, task.effectiveActive=?, task.status=?\n`;
  for (const ps of statusOrder) {
    if (!groups[ps]) continue;
    // Most common active pattern
    const activeEntries = Object.entries(activeGroups[ps] || {}).sort((a, b) => b[1] - a[1]);
    const taskEntries = Object.entries(groups[ps] || {}).sort((a, b) => b[1] - a[1]);
    const topActive = activeEntries[0] ? activeEntries[0][0] : "?";
    const topTask = taskEntries[0] ? taskEntries[0][0] : "?";
    r += `  ${ps}: most common = [${topActive}] taskStatus=${topTask}\n`;
  }

  return r;
})();
