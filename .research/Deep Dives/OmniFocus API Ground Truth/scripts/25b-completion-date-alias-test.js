// 25b — effectiveCompletionDate vs effectiveCompletedDate alias test
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Tests whether effectiveCompletionDate and effectiveCompletedDate
// are aliases returning the same value on tasks.

(() => {
  let r = `=== 25b: effectiveCompletionDate vs effectiveCompletedDate ===\n\n`;

  const tasks = flattenedTasks;
  let tested = 0;
  let bothNull = 0;
  let match = 0;
  let differ = 0;
  const samples = [];

  for (let i = 0; i < tasks.length; i++) {
    const t = tasks[i];
    const a = t.effectiveCompletionDate;
    const b = t.effectiveCompletedDate;

    // Only sample interesting cases (at least one non-null)
    if (a === null && b === null) {
      bothNull++;
      continue;
    }
    tested++;

    const aStr = a ? a.toISOString() : "null";
    const bStr = b ? b.toISOString() : "null";
    const same = aStr === bStr;

    if (same) match++;
    else differ++;

    if (samples.length < 10) {
      samples.push({
        name: t.name.substring(0, 40),
        completionDate: aStr,
        completedDate: bStr,
        same: same
      });
    }
  }

  r += `Total tasks: ${tasks.length}\n`;
  r += `Both null: ${bothNull}\n`;
  r += `At least one non-null: ${tested}\n`;
  r += `Match: ${match}\n`;
  r += `Differ: ${differ}\n`;

  r += `\n--- Samples (up to 10 with at least one non-null) ---\n`;
  for (let i = 0; i < samples.length; i++) {
    const s = samples[i];
    r += `  "${s.name}"\n`;
    r += `    effectiveCompletionDate: ${s.completionDate}\n`;
    r += `    effectiveCompletedDate:  ${s.completedDate}\n`;
    r += `    same? ${s.same}\n`;
  }

  // Also check: does completionDate exist alongside completedDate?
  r += `\n--- completionDate vs completedDate (non-effective) ---\n`;
  const t0 = tasks[0];
  r += `  task.completionDate: ${t0.completionDate === undefined ? "undefined" : (t0.completionDate === null ? "null" : t0.completionDate.toISOString())}\n`;
  try {
    const cd = t0.completedDate;
    r += `  task.completedDate: ${cd === undefined ? "undefined" : (cd === null ? "null" : cd.toISOString())}\n`;
  } catch(e) {
    r += `  task.completedDate: error — ${e.message}\n`;
  }

  // Check on a completed task specifically
  r += `\n--- On a completed task ---\n`;
  for (let i = 0; i < tasks.length; i++) {
    if (tasks[i].completed) {
      const ct = tasks[i];
      r += `  "${ct.name.substring(0, 40)}"\n`;
      r += `    completed: ${ct.completed}\n`;
      r += `    completionDate: ${ct.completionDate ? ct.completionDate.toISOString() : "null"}\n`;
      try {
        r += `    completedDate: ${ct.completedDate === undefined ? "undefined" : (ct.completedDate === null ? "null" : ct.completedDate.toISOString())}\n`;
      } catch(e) {
        r += `    completedDate: error — ${e.message}\n`;
      }
      r += `    effectiveCompletionDate: ${ct.effectiveCompletionDate ? ct.effectiveCompletionDate.toISOString() : "null"}\n`;
      r += `    effectiveCompletedDate: ${ct.effectiveCompletedDate ? ct.effectiveCompletedDate.toISOString() : "null"}\n`;
      break;
    }
  }

  return r;
})();
