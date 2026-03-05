// 24 — Date Inheritance Patterns
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Investigates how effective* dates are inherited.
// For tasks with effectiveDueDate but no direct dueDate, traces the
// inheritance source (project, parent task, or unknown).
// Same for defer dates.

(() => {
  let r = `=== 24: Date Inheritance Patterns ===\n\n`;

  const tasks = flattenedTasks;
  r += `Total tasks: ${tasks.length}\n\n`;

  // === Due Date Analysis ===
  r += `--- Due Date Inheritance ---\n`;
  let directDue = 0;
  let inheritedDue = 0;
  let noDue = 0;
  let dueFromProject = 0;
  let dueFromParent = 0;
  let dueFromUnknown = 0;
  const dueUnknownSamples = [];

  for (let i = 0; i < tasks.length; i++) {
    const t = tasks[i];
    if (!t.effectiveDueDate) { noDue++; continue; }
    if (t.dueDate) { directDue++; continue; }

    inheritedDue++;
    const effTime = t.effectiveDueDate.getTime();

    // Check containing project
    const cp = t.containingProject;
    if (cp && cp.dueDate && cp.dueDate.getTime() === effTime) {
      dueFromProject++;
      continue;
    }

    // Check parent task (direct parent)
    const pt = t.parent;
    if (pt) {
      // Check parent's direct dueDate
      if (pt.dueDate && pt.dueDate.getTime() === effTime) {
        dueFromParent++;
        continue;
      }
      // Check parent's effectiveDueDate (transitive)
      if (pt.effectiveDueDate && pt.effectiveDueDate.getTime() === effTime) {
        dueFromParent++;
        continue;
      }
    }

    dueFromUnknown++;
    if (dueUnknownSamples.length < 5) {
      dueUnknownSamples.push({
        name: t.name,
        effDue: t.effectiveDueDate.toISOString().slice(0, 10),
        projDue: cp ? (cp.dueDate ? cp.dueDate.toISOString().slice(0, 10) : "null") : "no project",
        parentDue: pt ? (pt.dueDate ? pt.dueDate.toISOString().slice(0, 10) : "null") : "no parent",
        parentEffDue: pt ? (pt.effectiveDueDate ? pt.effectiveDueDate.toISOString().slice(0, 10) : "null") : "no parent"
      });
    }
  }

  r += `  No effective due date: ${noDue}\n`;
  r += `  Direct due date (own): ${directDue}\n`;
  r += `  Inherited due date: ${inheritedDue}\n`;
  r += `    From project dueDate: ${dueFromProject}\n`;
  r += `    From parent task: ${dueFromParent}\n`;
  r += `    Unknown source: ${dueFromUnknown}\n`;

  if (dueUnknownSamples.length > 0) {
    r += `\n  Unknown due date samples:\n`;
    for (let i = 0; i < dueUnknownSamples.length; i++) {
      const s = dueUnknownSamples[i];
      r += `    "${s.name}": effDue=${s.effDue}, proj=${s.projDue}, parent=${s.parentDue}, parentEff=${s.parentEffDue}\n`;
    }
  }

  // === Defer Date Analysis ===
  r += `\n--- Defer Date Inheritance ---\n`;
  let directDefer = 0;
  let inheritedDefer = 0;
  let noDefer = 0;
  let deferFromProject = 0;
  let deferFromParent = 0;
  let deferFromUnknown = 0;
  const deferUnknownSamples = [];

  for (let i = 0; i < tasks.length; i++) {
    const t = tasks[i];
    if (!t.effectiveDeferDate) { noDefer++; continue; }
    if (t.deferDate) { directDefer++; continue; }

    inheritedDefer++;
    const effTime = t.effectiveDeferDate.getTime();

    const cp = t.containingProject;
    if (cp && cp.deferDate && cp.deferDate.getTime() === effTime) {
      deferFromProject++;
      continue;
    }

    const pt = t.parent;
    if (pt) {
      if (pt.deferDate && pt.deferDate.getTime() === effTime) {
        deferFromParent++;
        continue;
      }
      if (pt.effectiveDeferDate && pt.effectiveDeferDate.getTime() === effTime) {
        deferFromParent++;
        continue;
      }
    }

    deferFromUnknown++;
    if (deferUnknownSamples.length < 5) {
      deferUnknownSamples.push({
        name: t.name,
        effDefer: t.effectiveDeferDate.toISOString().slice(0, 10),
        projDefer: cp ? (cp.deferDate ? cp.deferDate.toISOString().slice(0, 10) : "null") : "no project",
        parentDefer: pt ? (pt.deferDate ? pt.deferDate.toISOString().slice(0, 10) : "null") : "no parent"
      });
    }
  }

  r += `  No effective defer date: ${noDefer}\n`;
  r += `  Direct defer date (own): ${directDefer}\n`;
  r += `  Inherited defer date: ${inheritedDefer}\n`;
  r += `    From project deferDate: ${deferFromProject}\n`;
  r += `    From parent task: ${deferFromParent}\n`;
  r += `    Unknown source: ${deferFromUnknown}\n`;

  if (deferUnknownSamples.length > 0) {
    r += `\n  Unknown defer date samples:\n`;
    for (let i = 0; i < deferUnknownSamples.length; i++) {
      const s = deferUnknownSamples[i];
      r += `    "${s.name}": effDefer=${s.effDefer}, proj=${s.projDefer}, parent=${s.parentDefer}\n`;
    }
  }

  // === Summary ===
  r += `\n--- Summary ---\n`;
  r += `Due dates: ${directDue} direct + ${inheritedDue} inherited = ${directDue + inheritedDue} with effective dates\n`;
  r += `Defer dates: ${directDefer} direct + ${inheritedDefer} inherited = ${directDefer + inheritedDefer} with effective dates\n`;
  r += `Inheritance is fully traceable: ${dueFromUnknown === 0 && deferFromUnknown === 0 ? "YES ✅" : "NO (some unknown sources)"}\n`;

  return r;
})();
