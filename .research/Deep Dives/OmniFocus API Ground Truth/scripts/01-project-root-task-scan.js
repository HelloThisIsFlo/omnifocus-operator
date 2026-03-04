// 01 — Project vs Root Task Full Scan
// READ-ONLY — no modifications to OmniFocus data
//
// Definitive scan of ALL fields on p.* vs p.task.* across every flattenedProject.
// Reports: task-only fields, effectiveCompletionDate tracking, status distributions,
// shared field divergence, inInbox distribution, id match verification.

(() => {
  const app = Application("OmniFocus");
  const doc = app.defaultDocument;
  const projects = doc.flattenedProjects();
  const total = projects.length;

  // --- Counters ---
  // Task-only fields (expected: undefined on p, defined on p.task)
  let taskOnly = { added: 0, modified: 0, active: 0, effectiveActive: 0 };
  let taskOnlyDefined = { added: 0, modified: 0, active: 0, effectiveActive: 0 };

  // effectiveCompletionDate special tracking
  let ecd = { pUndef_tNull: 0, pUndef_tDate: 0, pNull_tNull: 0, pDate_tDate_match: 0, pDate_tDate_diverge: 0, pDate_tNull: 0, pNull_tDate: 0 };

  // Status distributions
  let projectStatus = {};  // String(p.status) → count
  let taskStatus = {};     // String(p.task.status) → count

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

  // Examples collectors (first 3)
  let ecdExamples = [];  // p=undefined, t=Date
  let divergeExamples = {};

  for (let i = 0; i < total; i++) {
    const p = projects[i];
    const t = p.task();

    // --- Task-only fields ---
    for (const f of ["added", "modified", "active", "effectiveActive"]) {
      const pv = p[f]();
      const tv = t[f]();
      if (pv === undefined || pv === null) taskOnly[f]++;
      if (tv !== undefined && tv !== null) taskOnlyDefined[f]++;
    }

    // --- active/effectiveActive distributions ---
    const tActive = t.active();
    const tEffActive = t.effectiveActive();
    if (tActive === true) activeTrue++;
    else if (tActive === false) activeFalse++;
    if (tEffActive === true) effActiveTrue++;
    else if (tEffActive === false) effActiveFalse++;

    // --- effectiveCompletionDate special tracking ---
    const pecd = p.effectiveCompletionDate();
    const tecd = t.effectiveCompletionDate();
    const pecdIsDate = pecd instanceof Date;
    const tecdIsDate = tecd instanceof Date;
    if (pecd === undefined && tecd === null) ecd.pUndef_tNull++;
    else if (pecd === undefined && tecdIsDate) {
      ecd.pUndef_tDate++;
      if (ecdExamples.length < 3) ecdExamples.push(p.name());
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
      const ps = p.status();
      const psKey = (ps === null || ps === undefined) ? "null/undefined" : String(ps);
      projectStatus[psKey] = (projectStatus[psKey] || 0) + 1;
    } catch(e) {
      projectStatus["ERROR"] = (projectStatus["ERROR"] || 0) + 1;
    }

    try {
      const tst = t.status();
      const tstKey = (tst === null || tst === undefined) ? "null/undefined" : String(tst);
      taskStatus[tstKey] = (taskStatus[tstKey] || 0) + 1;
    } catch(e) {
      taskStatus["ERROR"] = (taskStatus["ERROR"] || 0) + 1;
    }

    // --- ID match ---
    if (p.id() === t.id()) idMatch++;
    else idMismatch++;

    // --- Shared field divergence ---
    sharedChecked++;
    const checks = [
      ["name", p.name(), t.name()],
      ["note", p.note(), t.note()],
      ["completed", p.completed(), t.completed()],
      ["completedByChildren", p.completedByChildren(), t.completedByChildren()],
      ["flagged", p.flagged(), t.flagged()],
      ["effectiveFlagged", p.effectiveFlagged(), t.effectiveFlagged()],
      ["sequential", p.sequential(), t.sequential()],
      ["estimatedMinutes", p.estimatedMinutes(), t.estimatedMinutes()],
      ["hasChildren", p.hasChildren(), t.hasChildren()],
      ["shouldUseFloatingTimeZone", p.shouldUseFloatingTimeZone(), t.shouldUseFloatingTimeZone()],
    ];

    // Date fields (compare by getTime() for Dates, direct for null)
    const dateFields = ["dueDate", "deferDate", "completionDate", "plannedDate", "dropDate",
                        "effectiveDueDate", "effectiveDeferDate"];
    for (const df of dateFields) {
      const pv = p[df]();
      const tv = t[df]();
      const pvDate = pv instanceof Date;
      const tvDate = tv instanceof Date;
      if (pvDate && tvDate) {
        if (pv.getTime() !== tv.getTime()) {
          shared[df]++;
          if (!divergeExamples[df]) divergeExamples[df] = p.name();
        }
      } else if (pv !== tv) {
        // One is null/undefined and other is not
        if (!((pv === null || pv === undefined) && (tv === null || tv === undefined))) {
          shared[df]++;
          if (!divergeExamples[df]) divergeExamples[df] = p.name();
        }
      }
    }

    for (const [field, pv, tv] of checks) {
      if (pv !== tv) {
        shared[field]++;
        if (!divergeExamples[field]) divergeExamples[field] = p.name();
      }
    }

    // --- inInbox on task ---
    const inbox = t.inInbox();
    if (inbox === true) inInboxTrue++;
    else if (inbox === false) inInboxFalse++;
    else inInboxUndef++;
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

  r += `\n--- effectiveCompletionDate ---\n`;
  r += `  p=undefined, t=null: ${ecd.pUndef_tNull}\n`;
  r += `  p=undefined, t=Date: ${ecd.pUndef_tDate}\n`;
  r += `  p=null, t=null: ${ecd.pNull_tNull}\n`;
  r += `  both Date, match: ${ecd.pDate_tDate_match}\n`;
  r += `  both Date, diverge: ${ecd.pDate_tDate_diverge}\n`;
  r += `  p=Date, t=null: ${ecd.pDate_tNull}\n`;
  r += `  p=null, t=Date: ${ecd.pNull_tDate}\n`;
  if (ecdExamples.length > 0) r += `  Examples (p=undef,t=Date): ${ecdExamples.join(", ")}\n`;

  r += `\n--- Project.Status Distribution (String()) ---\n`;
  for (const [k, v] of Object.entries(projectStatus)) r += `  "${k}": ${v}\n`;

  r += `\n--- Task.Status Distribution (String() on p.task) ---\n`;
  for (const [k, v] of Object.entries(taskStatus)) r += `  "${k}": ${v}\n`;

  r += `\n--- ID Match (p.id === p.task.id) ---\n`;
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

  r += `\n--- inInbox on p.task ---\n`;
  r += `  true: ${inInboxTrue}, false: ${inInboxFalse}, undefined: ${inInboxUndef}\n`;

  return r;
})();
