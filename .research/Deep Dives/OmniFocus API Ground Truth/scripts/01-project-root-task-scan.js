// 01 — Project vs Root Task Full Scan
// READ-ONLY — no modifications to OmniFocus data
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Definitive scan of ALL fields on p.* vs p.task.* across every flattenedProject.
// Reports: task-only fields, project-specific fields (review, folder, singleton,
// repetitionRule), effectiveCompletedDate tracking, status distributions,
// shared field divergence, inInbox distribution, id match verification.

(() => {
  const projects = flattenedProjects;
  const total = projects.length;

  // --- Enum-to-string helpers (String() returns "[object Object]" in Omni Automation) ---
  function projectStatusName(s) {
    if (s === null || s === undefined) return "null/undefined";
    if (s === Project.Status.Active) return "Active";
    if (s === Project.Status.OnHold) return "OnHold";
    if (s === Project.Status.Done) return "Done";
    if (s === Project.Status.Dropped) return "Dropped";
    return "UNKNOWN";
  }

  function taskStatusName(s) {
    if (s === null || s === undefined) return "null/undefined";
    if (s === Task.Status.Available) return "Available";
    if (s === Task.Status.Blocked) return "Blocked";
    if (s === Task.Status.Completed) return "Completed";
    if (s === Task.Status.Dropped) return "Dropped";
    if (s === Task.Status.DueSoon) return "DueSoon";
    if (s === Task.Status.Next) return "Next";
    if (s === Task.Status.Overdue) return "Overdue";
    return "UNKNOWN";
  }

  // --- Counters ---
  // Task-only fields (expected: undefined on p, defined on p.task)
  let taskOnly = { added: 0, modified: 0, active: 0, effectiveActive: 0 };
  let taskOnlyDefined = { added: 0, modified: 0, active: 0, effectiveActive: 0 };

  // effectiveCompletedDate special tracking
  let ecd = { pUndef_tNull: 0, pUndef_tDate: 0, pUndef_tUndef: 0, pNull_tNull: 0, pDate_tDate_match: 0, pDate_tDate_diverge: 0, pDate_tNull: 0, pNull_tDate: 0 };

  // Status distributions
  let projectStatus = {};
  let taskStatus = {};

  // ID match
  let idMatch = 0, idMismatch = 0;

  // Shared field divergence counters
  let shared = {
    name: 0, note: 0, completed: 0, completedByChildren: 0,
    flagged: 0, effectiveFlagged: 0, sequential: 0,
    dueDate: 0, deferDate: 0, completionDate: 0,
    plannedDate: 0, dropDate: 0,
    effectiveDueDate: 0, effectiveDeferDate: 0,
    estimatedMinutes: 0, hasChildren: 0,
    shouldUseFloatingTimeZone: 0
  };
  let sharedChecked = 0;

  // inInbox on task
  let inInboxTrue = 0, inInboxFalse = 0, inInboxUndef = 0;

  // active/effectiveActive distributions (on p.task)
  let activeTrue = 0, activeFalse = 0;
  let effActiveTrue = 0, effActiveFalse = 0;

  // --- Project-Specific Field Counters ---
  let projSpecific = {
    containsSingletonActions: { true: 0, false: 0, error: 0 },
    lastReviewDate: { present: 0, missing: 0, error: 0 },
    nextReviewDate: { present: 0, missing: 0, error: 0 },
    reviewInterval: { present: 0, missing: 0, error: 0 },
    nextTask: { present: 0, missing: 0, error: 0 },
    folder: { present: 0, missing: 0, error: 0 },
    repetitionRule: { present: 0, missing: 0, error: 0 }
  };
  let reviewIntervalValues = {};  // "steps:unit" → count
  let repRuleExamples = [];       // first 3 with repetitionRule
  let tagsDiverge = 0, tagsMatch = 0;

  // Examples collectors (first 3)
  let ecdExamples = [];  // p=undefined, t=Date
  let divergeExamples = {};

  for (let i = 0; i < total; i++) {
    const p = projects[i];
    const t = p.task;

    // --- Task-only fields ---
    for (const f of ["added", "modified", "active", "effectiveActive"]) {
      const pv = p[f];
      const tv = t[f];
      if (pv === undefined || pv === null) taskOnly[f]++;
      if (tv !== undefined && tv !== null) taskOnlyDefined[f]++;
    }

    // --- active/effectiveActive distributions ---
    const tActive = t.active;
    const tEffActive = t.effectiveActive;
    if (tActive === true) activeTrue++;
    else if (tActive === false) activeFalse++;
    if (tEffActive === true) effActiveTrue++;
    else if (tEffActive === false) effActiveFalse++;

    // --- effectiveCompletedDate special tracking ---
    const pecd = p.effectiveCompletedDate;
    const tecd = t.effectiveCompletedDate;
    const pecdIsDate = pecd instanceof Date;
    const tecdIsDate = tecd instanceof Date;
    if (pecd === undefined && tecd === undefined) ecd.pUndef_tUndef++;
    else if (pecd === undefined && tecd === null) ecd.pUndef_tNull++;
    else if (pecd === undefined && tecdIsDate) {
      ecd.pUndef_tDate++;
      if (ecdExamples.length < 3) ecdExamples.push(p.name);
    }
    else if (pecd === null && tecd === null) ecd.pNull_tNull++;
    else if (pecdIsDate && tecdIsDate) {
      if (pecd.getTime() === tecd.getTime()) ecd.pDate_tDate_match++;
      else ecd.pDate_tDate_diverge++;
    }
    else if (pecdIsDate && tecd === null) ecd.pDate_tNull++;
    else if (pecd === null && tecdIsDate) ecd.pNull_tDate++;

    // --- Status distributions ---
    try {
      const ps = p.status;
      const psKey = projectStatusName(ps);
      projectStatus[psKey] = (projectStatus[psKey] || 0) + 1;
    } catch(e) {
      projectStatus["ERROR"] = (projectStatus["ERROR"] || 0) + 1;
    }

    try {
      const tst = t.taskStatus;
      const tstKey = taskStatusName(tst);
      taskStatus[tstKey] = (taskStatus[tstKey] || 0) + 1;
    } catch(e) {
      taskStatus["ERROR"] = (taskStatus["ERROR"] || 0) + 1;
    }

    // --- ID match ---
    if (p.id.primaryKey === t.id.primaryKey) idMatch++;
    else idMismatch++;

    // --- Shared field divergence ---
    sharedChecked++;
    const checks = [
      ["name", p.name, t.name],
      ["note", p.note, t.note],
      ["completed", p.completed, t.completed],
      ["completedByChildren", p.completedByChildren, t.completedByChildren],
      ["flagged", p.flagged, t.flagged],
      ["effectiveFlagged", p.effectiveFlagged, t.effectiveFlagged],
      ["sequential", p.sequential, t.sequential],
      ["estimatedMinutes", p.estimatedMinutes, t.estimatedMinutes],
      ["hasChildren", p.hasChildren, t.hasChildren],
      ["shouldUseFloatingTimeZone", p.shouldUseFloatingTimeZone, t.shouldUseFloatingTimeZone],
    ];

    // Date fields (compare by getTime() for Dates, direct for null)
    const dateFields = ["dueDate", "deferDate", "completionDate", "plannedDate", "dropDate",
                        "effectiveDueDate", "effectiveDeferDate"];
    for (const df of dateFields) {
      const pv = p[df];
      const tv = t[df];
      const pvDate = pv instanceof Date;
      const tvDate = tv instanceof Date;
      if (pvDate && tvDate) {
        if (pv.getTime() !== tv.getTime()) {
          shared[df]++;
          if (!divergeExamples[df]) divergeExamples[df] = p.name;
        }
      } else if (pv !== tv) {
        // One is null/undefined and other is not
        if (!((pv === null || pv === undefined) && (tv === null || tv === undefined))) {
          shared[df]++;
          if (!divergeExamples[df]) divergeExamples[df] = p.name;
        }
      }
    }

    for (const [field, pv, tv] of checks) {
      if (pv !== tv) {
        shared[field]++;
        if (!divergeExamples[field]) divergeExamples[field] = p.name;
      }
    }

    // --- inInbox on task ---
    const inbox = t.inInbox;
    if (inbox === true) inInboxTrue++;
    else if (inbox === false) inInboxFalse++;
    else inInboxUndef++;

    // --- Project-Specific Fields ---
    try {
      const csa = p.containsSingletonActions;
      if (csa === true) projSpecific.containsSingletonActions.true++;
      else projSpecific.containsSingletonActions.false++;
    } catch(e) { projSpecific.containsSingletonActions.error++; }

    try {
      const lrd = p.lastReviewDate;
      if (lrd instanceof Date) projSpecific.lastReviewDate.present++;
      else projSpecific.lastReviewDate.missing++;
    } catch(e) { projSpecific.lastReviewDate.error++; }

    try {
      const nrd = p.nextReviewDate;
      if (nrd instanceof Date) projSpecific.nextReviewDate.present++;
      else projSpecific.nextReviewDate.missing++;
    } catch(e) { projSpecific.nextReviewDate.error++; }

    try {
      const riVal = p.reviewInterval;
      if (riVal) {
        projSpecific.reviewInterval.present++;
        try {
          const steps = riVal.steps;
          const unit = riVal.unit;
          const key = `${steps}:${unit}`;
          reviewIntervalValues[key] = (reviewIntervalValues[key] || 0) + 1;
        } catch(e2) { /* sub-property probe failed */ }
      } else {
        projSpecific.reviewInterval.missing++;
      }
    } catch(e) { projSpecific.reviewInterval.error++; }

    try {
      const nt = p.nextTask;
      if (nt) projSpecific.nextTask.present++;
      else projSpecific.nextTask.missing++;
    } catch(e) { projSpecific.nextTask.error++; }

    try {
      const fol = p.parentFolder;
      if (fol) projSpecific.folder.present++;
      else projSpecific.folder.missing++;
    } catch(e) { projSpecific.folder.error++; }

    try {
      const rrVal = p.repetitionRule;
      if (rrVal) {
        projSpecific.repetitionRule.present++;
        if (repRuleExamples.length < 3) {
          let ex = { name: p.name };
          try { ex.ruleString = rrVal.ruleString; } catch(e2) { ex.ruleString = "ERROR"; }
          try {
            const st = rrVal.scheduleType;
            ex.scheduleType = st && st.name ? st.name : String(st);
          } catch(e2) { ex.scheduleType = "ERROR"; }
          repRuleExamples.push(ex);
        }
      } else {
        projSpecific.repetitionRule.missing++;
      }
    } catch(e) { projSpecific.repetitionRule.error++; }

    // tags divergence: p.tags vs p.task.tags — compare sorted names
    try {
      const pNames = p.tags.map(tg => tg.name).sort().join(",");
      const tNames = t.tags.map(tg => tg.name).sort().join(",");
      if (pNames === tNames) tagsMatch++;
      else tagsDiverge++;
    } catch(e) { /* skip */ }
  }

  // --- Report ---
  let r = `=== 01: Project vs Root Task Full Scan ===\n`;
  r += `Total projects: ${total}\n\n`;

  r += `--- Task-Only Fields (undefined/null on p.*, defined on p.task.*) ---\n`;
  for (const f of ["added", "modified", "active", "effectiveActive"]) {
    r += `  ${f}: p=undef/null in ${taskOnly[f]}/${total}, t=defined in ${taskOnlyDefined[f]}/${total}\n`;
  }

  r += `\n--- active / effectiveActive Distribution (on p.task) ---\n`;
  r += `  active: true=${activeTrue}, false=${activeFalse}\n`;
  r += `  effectiveActive: true=${effActiveTrue}, false=${effActiveFalse}\n`;
  r += `  Divergence (active but not effectiveActive): ${activeTrue - effActiveTrue}\n`;

  r += `\n--- effectiveCompletedDate ---\n`;
  r += `  p=undefined, t=undefined: ${ecd.pUndef_tUndef}\n`;
  r += `  p=undefined, t=null: ${ecd.pUndef_tNull}\n`;
  r += `  p=undefined, t=Date: ${ecd.pUndef_tDate}\n`;
  r += `  p=null, t=null: ${ecd.pNull_tNull}\n`;
  r += `  both Date, match: ${ecd.pDate_tDate_match}\n`;
  r += `  both Date, diverge: ${ecd.pDate_tDate_diverge}\n`;
  r += `  p=Date, t=null: ${ecd.pDate_tNull}\n`;
  r += `  p=null, t=Date: ${ecd.pNull_tDate}\n`;
  if (ecdExamples.length > 0) r += `  Examples (p=undef,t=Date): ${ecdExamples.join(", ")}\n`;
  const ecdSum = ecd.pUndef_tUndef + ecd.pUndef_tNull + ecd.pUndef_tDate + ecd.pNull_tNull + ecd.pDate_tDate_match + ecd.pDate_tDate_diverge + ecd.pDate_tNull + ecd.pNull_tDate;
  r += `  Sum check: ${ecdSum}/${total} ${ecdSum === total ? "✅" : "❌ MISMATCH"}\n`;

  r += `\n--- Project.Status Distribution ---\n`;
  for (const [k, v] of Object.entries(projectStatus)) r += `  "${k}": ${v}\n`;
  const projStatusSum = Object.values(projectStatus).reduce((a, b) => a + b, 0);
  r += `  Sum check: ${projStatusSum}/${total} ${projStatusSum === total ? "✅" : "❌ MISMATCH"}\n`;

  r += `\n--- Task.Status Distribution (on p.task) ---\n`;
  for (const [k, v] of Object.entries(taskStatus)) r += `  "${k}": ${v}\n`;
  const taskStatusSum = Object.values(taskStatus).reduce((a, b) => a + b, 0);
  r += `  Sum check: ${taskStatusSum}/${total} ${taskStatusSum === total ? "✅" : "❌ MISMATCH"}\n`;

  r += `\n--- ID Match (p.id.primaryKey === p.task.id.primaryKey) ---\n`;
  r += `  Match: ${idMatch}, Mismatch: ${idMismatch}\n`;

  r += `\n--- Shared Field Divergence (out of ${sharedChecked} projects) ---\n`;
  let anyDiverge = false;
  for (const [field, count] of Object.entries(shared)) {
    if (count > 0) {
      anyDiverge = true;
      r += `  ${field}: ${count} divergences`;
      if (divergeExamples[field]) r += ` (e.g., "${divergeExamples[field]}")`;
      r += `\n`;
    }
  }
  if (!anyDiverge) r += `  ✅ ZERO divergences on all shared fields\n`;

  r += `\n--- Project-Specific Fields ---\n`;
  r += `  containsSingletonActions: true=${projSpecific.containsSingletonActions.true}, false=${projSpecific.containsSingletonActions.false}, error=${projSpecific.containsSingletonActions.error}\n`;
  r += `  lastReviewDate: present=${projSpecific.lastReviewDate.present}, missing=${projSpecific.lastReviewDate.missing}, error=${projSpecific.lastReviewDate.error}\n`;
  r += `  nextReviewDate: present=${projSpecific.nextReviewDate.present}, missing=${projSpecific.nextReviewDate.missing}, error=${projSpecific.nextReviewDate.error}\n`;
  r += `  reviewInterval: present=${projSpecific.reviewInterval.present}, missing=${projSpecific.reviewInterval.missing}, error=${projSpecific.reviewInterval.error}\n`;
  if (Object.keys(reviewIntervalValues).length > 0) {
    r += `  reviewInterval values:\n`;
    for (const [k, v] of Object.entries(reviewIntervalValues).sort((a, b) => b[1] - a[1])) {
      r += `    "${k}": ${v}\n`;
    }
  }
  r += `  nextTask: present=${projSpecific.nextTask.present}, missing=${projSpecific.nextTask.missing}, error=${projSpecific.nextTask.error}\n`;
  r += `  folder: present=${projSpecific.folder.present}, missing=${projSpecific.folder.missing} (top-level), error=${projSpecific.folder.error}\n`;
  r += `  repetitionRule: present=${projSpecific.repetitionRule.present}, missing=${projSpecific.repetitionRule.missing}, error=${projSpecific.repetitionRule.error}\n`;
  if (repRuleExamples.length > 0) {
    r += `  repetitionRule examples:\n`;
    for (const ex of repRuleExamples) {
      r += `    "${ex.name}": ruleString=${ex.ruleString}, scheduleType=${ex.scheduleType}\n`;
    }
  }
  r += `  tags (p vs p.task): match=${tagsMatch}, diverge=${tagsDiverge}\n`;

  r += `\n--- inInbox on p.task ---\n`;
  r += `  true: ${inInboxTrue}, false: ${inInboxFalse}, undefined: ${inInboxUndef}\n`;

  return r;
})();
