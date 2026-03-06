// 19 — completedByChildren Analysis
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Investigates what completedByChildren actually controls.
// Finds parent tasks and checks whether the flag correlates with
// auto-completion behavior.

(() => {
  let r = `=== 19: completedByChildren Analysis ===\n\n`;

  const tasks = flattenedTasks;

  // Find parent tasks
  const parents = [];
  for (let i = 0; i < tasks.length; i++) {
    if (tasks[i].hasChildren) {
      parents.push(tasks[i]);
    }
  }

  r += `Total tasks: ${tasks.length}\n`;
  r += `Parent tasks (hasChildren=true): ${parents.length}\n\n`;

  // Analyze by completedByChildren value
  let cbcTrue = 0, cbcFalse = 0;
  let cbcTrueCompleted = 0, cbcFalseCompleted = 0;
  let cbcTrueAllDone = 0, cbcFalseAllDone = 0;
  let cbcTrueAllDoneAndComplete = 0, cbcFalseAllDoneAndComplete = 0;
  let cbcTrueAllDoneButIncomplete = 0, cbcFalseAllDoneButIncomplete = 0;

  const interestingCases = [];

  for (let i = 0; i < parents.length; i++) {
    const p = parents[i];
    const children = p.children;
    const cbc = p.completedByChildren;

    // Check children completion
    let allComplete = true;
    let childCount = children.length;
    let completeCount = 0;

    for (let j = 0; j < children.length; j++) {
      if (children[j].completed) {
        completeCount++;
      } else {
        allComplete = false;
      }
    }

    if (cbc) {
      cbcTrue++;
      if (p.completed) cbcTrueCompleted++;
      if (allComplete && childCount > 0) {
        cbcTrueAllDone++;
        if (p.completed) cbcTrueAllDoneAndComplete++;
        else cbcTrueAllDoneButIncomplete++;
      }
    } else {
      cbcFalse++;
      if (p.completed) cbcFalseCompleted++;
      if (allComplete && childCount > 0) {
        cbcFalseAllDone++;
        if (p.completed) cbcFalseAllDoneAndComplete++;
        else cbcFalseAllDoneButIncomplete++;
      }
    }

    // Capture interesting cases: all children done
    if (allComplete && childCount > 0 && interestingCases.length < 15) {
      interestingCases.push({
        name: p.name,
        cbc: cbc,
        parentCompleted: p.completed,
        childCount: childCount,
        completeCount: completeCount
      });
    }
  }

  r += `--- completedByChildren=true ---\n`;
  r += `  Total parents: ${cbcTrue}\n`;
  r += `  Parent completed: ${cbcTrueCompleted}\n`;
  r += `  All children complete: ${cbcTrueAllDone}\n`;
  r += `    → Parent also completed: ${cbcTrueAllDoneAndComplete}\n`;
  r += `    → Parent NOT completed: ${cbcTrueAllDoneButIncomplete}\n`;

  r += `\n--- completedByChildren=false ---\n`;
  r += `  Total parents: ${cbcFalse}\n`;
  r += `  Parent completed: ${cbcFalseCompleted}\n`;
  r += `  All children complete: ${cbcFalseAllDone}\n`;
  r += `    → Parent also completed: ${cbcFalseAllDoneAndComplete}\n`;
  r += `    → Parent NOT completed: ${cbcFalseAllDoneButIncomplete}\n`;

  r += `\n--- Cases Where All Children Are Complete (first 15) ---\n`;
  if (interestingCases.length === 0) {
    r += `  No cases found.\n`;
  } else {
    for (let i = 0; i < interestingCases.length; i++) {
      const c = interestingCases[i];
      r += `  "${c.name}" | cbc=${c.cbc} | parentCompleted=${c.parentCompleted}`;
      r += ` | children: ${c.completeCount}/${c.childCount}\n`;
    }
  }

  r += `\n--- Interpretation ---\n`;
  r += `If cbc=true + all children done → parent completed=true in most cases:\n`;
  r += `  Then cbc controls auto-completion.\n`;
  r += `If cbc=true + all children done → parent completed=false:\n`;
  r += `  Then cbc does NOT trigger auto-completion (just a UI hint).\n`;

  return r;
})();
