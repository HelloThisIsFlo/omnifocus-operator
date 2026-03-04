// 02 — Project Effective Fields
// READ-ONLY — no modifications to OmniFocus data
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Checks ALL 6 "effective*" fields for the undefined-on-project bug.
// Determines whether effectiveCompletedDate is the ONLY broken field,
// or if others have the same issue.

(() => {
  const projects = flattenedProjects;
  const total = projects.length;

  const fields = [
    "effectiveDueDate",
    "effectiveDeferDate",
    "effectiveCompletedDate",
    "effectivePlannedDate",
    "effectiveDropDate",
    "effectiveFlagged"
  ];

  // For each field: track 5 categories
  let counters = {};
  let examples = {};  // first 3 examples of p=undefined, t=value
  for (const f of fields) {
    counters[f] = {
      pUndef_tNull: 0,    // p=undefined, t=null → field doesn't exist on project
      pUndef_tValue: 0,   // p=undefined, t=has value → BROKEN on project
      bothNull: 0,        // both null/undefined → neither has it
      bothMatch: 0,       // both have value and match → proxied correctly
      diverge: 0          // both have value but differ → unexpected
    };
    examples[f] = [];
  }

  for (let i = 0; i < total; i++) {
    const p = projects[i];
    const t = p.task;

    for (const f of fields) {
      const pv = p[f];
      const tv = t[f];
      const c = counters[f];

      const pvMissing = (pv === undefined || pv === null);
      const tvMissing = (tv === undefined || tv === null);
      const pvIsUndef = (pv === undefined);

      if (pvIsUndef && tvMissing) {
        c.pUndef_tNull++;
      } else if (pvIsUndef && !tvMissing) {
        c.pUndef_tValue++;
        if (examples[f].length < 3) {
          examples[f].push({ name: p.name, tValue: String(tv) });
        }
      } else if (pvMissing && tvMissing) {
        c.bothNull++;
      } else if (!pvMissing && !tvMissing) {
        // Both have values — compare
        if (f === "effectiveFlagged") {
          // Boolean comparison
          if (pv === tv) c.bothMatch++;
          else c.diverge++;
        } else {
          // Date comparison
          if (pv instanceof Date && tv instanceof Date && pv.getTime() === tv.getTime()) {
            c.bothMatch++;
          } else {
            c.diverge++;
          }
        }
      } else {
        c.diverge++;
      }
    }
  }

  // --- Report ---
  let r = `=== 02: Project Effective Fields ===\n`;
  r += `Total projects: ${total}\n\n`;

  for (const f of fields) {
    const c = counters[f];
    r += `--- ${f} ---\n`;
    r += `  p=undefined, t=null:    ${c.pUndef_tNull}\n`;
    r += `  p=undefined, t=value:   ${c.pUndef_tValue}`;
    if (c.pUndef_tValue > 0) r += `  ⚠️ BROKEN ON PROJECT`;
    r += `\n`;
    r += `  both null:              ${c.bothNull}\n`;
    r += `  both match:             ${c.bothMatch}\n`;
    r += `  diverge:                ${c.diverge}`;
    if (c.diverge > 0) r += `  ⚠️ UNEXPECTED`;
    r += `\n`;

    if (examples[f].length > 0) {
      r += `  Examples (p=undef, t=value):\n`;
      for (const ex of examples[f]) {
        r += `    "${ex.name}" → t=${ex.tValue}\n`;
      }
    }
    r += `\n`;
  }

  // Summary
  r += `--- Summary ---\n`;
  let brokenFields = [];
  let workingFields = [];
  for (const f of fields) {
    if (counters[f].pUndef_tValue > 0 || counters[f].pUndef_tNull > 0) {
      if (counters[f].bothMatch === 0) brokenFields.push(f);
      else workingFields.push(f);
    } else {
      workingFields.push(f);
    }
  }
  r += `Broken on project (must read from p.task): ${brokenFields.length > 0 ? brokenFields.join(", ") : "NONE"}\n`;
  r += `Working on project (proxied correctly): ${workingFields.length > 0 ? workingFields.join(", ") : "NONE"}\n`;

  return r;
})();
