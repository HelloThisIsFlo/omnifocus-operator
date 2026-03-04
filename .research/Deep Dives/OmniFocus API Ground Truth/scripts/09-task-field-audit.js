// 09 — Task Field Audit
// READ-ONLY — no modifications to OmniFocus data
//
// Scans ALL flattenedTasks with counter-based approach.
// Covers: name, added/modified, active/effectiveActive, inInbox, status distribution,
// project/parent/assignedContainer relationships, estimatedMinutes (3 categories),
// flags, tags, sequential, completedByChildren, hasChildren, repetitionRule
// (deep inspection), collections (linkedFileURLs, notifications, attachments),
// accessor equivalence (project vs containingProject, parentTask vs parent),
// shouldUseFloatingTimeZone, notes.

(() => {
  const app = Application("OmniFocus");
  const doc = app.defaultDocument;
  const tasks = doc.flattenedTasks();
  const total = tasks.length;

  let r = `=== 09: Task Field Audit ===\n`;
  r += `Total tasks: ${total}\n\n`;

  // --- Counters ---
  let added = { present: 0, missing: 0 };
  let modified = { present: 0, missing: 0 };
  let active = { true: 0, false: 0, other: 0 };
  let effActive = { true: 0, false: 0, other: 0 };
  let inInbox = { true: 0, false: 0, other: 0 };
  let completed = { true: 0, false: 0 };

  // Status distribution
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
  let statusDist = {};

  // Relationships
  let projectNull = 0, projectPresent = 0;
  let parentNull = 0, parentPresent = 0;
  let assignedContainerNull = 0, assignedContainerPresent = 0;

  // Dates
  let dateCounts = {};
  const dateFields = ["dueDate", "deferDate", "completionDate", "plannedDate", "dropDate",
                      "effectiveDueDate", "effectiveDeferDate", "effectiveCompletionDate",
                      "effectivePlannedDate", "effectiveDropDate"];
  for (const f of dateFields) dateCounts[f] = { present: 0, missing: 0 };

  // Estimated minutes (3 categories)
  let estMin = { null_or_undefined: 0, zero: 0, positive: 0 };

  // Flags
  let flagged = { true: 0, false: 0 };
  let effFlagged = { true: 0, false: 0 };
  let flagDiverge = 0;

  // Tags
  let tagCounts = { zero: 0, one: 0, multi: 0 };
  let maxTags = 0;

  // Sequential, completedByChildren, hasChildren
  let sequential = { true: 0, false: 0 };
  let completedByChildren = { true: 0, false: 0 };
  let hasChildren = { true: 0, false: 0 };

  // RepetitionRule
  let repRule = { present: 0, missing: 0 };

  // shouldUseFloatingTimeZone
  let floatingTZ = { true: 0, false: 0 };

  // Note presence
  let notePresent = 0, noteEmpty = 0;

  // Name field
  let namePresent = 0, nameEmpty = 0;

  // RepetitionRule deep inspection (first 5)
  let repRuleDeep = [];

  // Collections probing
  let collections = {
    linkedFileURLs: { nonEmpty: 0, empty: 0, error: 0 },
    notifications: { nonEmpty: 0, empty: 0, error: 0 },
    attachments: { nonEmpty: 0, empty: 0, error: 0 }
  };

  // Accessor equivalence (first 10)
  let accessorChecks = [];
  let accessorSummary = { projectMatch: 0, projectDiffer: 0, parentMatch: 0, parentDiffer: 0 };

  for (let i = 0; i < total; i++) {
    const t = tasks[i];

    // added/modified
    const a = t.added();
    const m = t.modified();
    if (a instanceof Date) added.present++; else added.missing++;
    if (m instanceof Date) modified.present++; else modified.missing++;

    // active/effectiveActive
    const act = t.active();
    if (act === true) active.true++; else if (act === false) active.false++; else active.other++;
    const ea = t.effectiveActive();
    if (ea === true) effActive.true++; else if (ea === false) effActive.false++; else effActive.other++;

    // inInbox
    const inbox = t.inInbox();
    if (inbox === true) inInbox.true++; else if (inbox === false) inInbox.false++; else inInbox.other++;

    // completed
    if (t.completed()) completed.true++; else completed.false++;

    // status
    const s = matchTaskStatus(t.status());
    statusDist[s] = (statusDist[s] || 0) + 1;

    // relationships
    try {
      const proj = t.project();
      if (proj) projectPresent++; else projectNull++;
    } catch(e) { projectNull++; }

    try {
      const par = t.parentTask();
      if (par) parentPresent++; else parentNull++;
    } catch(e) { parentNull++; }

    try {
      const ac = t.assignedContainer();
      if (ac) assignedContainerPresent++; else assignedContainerNull++;
    } catch(e) { assignedContainerNull++; }

    // dates
    for (const f of dateFields) {
      const v = t[f]();
      if (v instanceof Date) dateCounts[f].present++;
      else dateCounts[f].missing++;
    }

    // estimatedMinutes (3 categories)
    const em = t.estimatedMinutes();
    if (em === null || em === undefined) estMin.null_or_undefined++;
    else if (em === 0) estMin.zero++;
    else estMin.positive++;

    // flags
    const fl = t.flagged();
    const efl = t.effectiveFlagged();
    if (fl) flagged.true++; else flagged.false++;
    if (efl) effFlagged.true++; else effFlagged.false++;
    if (fl !== efl) flagDiverge++;

    // tags
    const tagList = t.tags();
    const tc = tagList.length;
    if (tc === 0) tagCounts.zero++;
    else if (tc === 1) tagCounts.one++;
    else tagCounts.multi++;
    if (tc > maxTags) maxTags = tc;

    // sequential, completedByChildren, hasChildren
    if (t.sequential()) sequential.true++; else sequential.false++;
    if (t.completedByChildren()) completedByChildren.true++; else completedByChildren.false++;
    if (t.hasChildren()) hasChildren.true++; else hasChildren.false++;

    // repetitionRule
    const rr = t.repetitionRule();
    if (rr) repRule.present++; else repRule.missing++;

    // floatingTZ
    if (t.shouldUseFloatingTimeZone()) floatingTZ.true++; else floatingTZ.false++;

    // note
    const note = t.note();
    if (note && note.length > 0) notePresent++; else noteEmpty++;

    // name
    const nm = t.name();
    if (nm && nm.length > 0) namePresent++; else nameEmpty++;

    // RepetitionRule deep inspection (first 5 that have one)
    if (rr && repRuleDeep.length < 5) {
      let deep = { index: i, name: nm };
      try { deep.ruleString = rr.ruleString(); deep.ruleStringType = typeof deep.ruleString; } catch(e) { deep.ruleString = "ERROR: " + e.message; }
      try { deep.scheduleType = rr.scheduleType(); deep.scheduleTypeType = typeof deep.scheduleType; } catch(e) { deep.scheduleType = "ERROR: " + e.message; }
      try { deep.fixedInterval = rr.fixedInterval(); deep.fixedIntervalType = typeof deep.fixedInterval; } catch(e) { deep.fixedInterval = "ERROR: " + e.message; }
      try { deep.unit = rr.unit(); deep.unitType = typeof deep.unit; } catch(e) { deep.unit = "ERROR: " + e.message; }
      repRuleDeep.push(deep);
    }

    // Collections probing
    for (const col of ["linkedFileURLs", "notifications", "attachments"]) {
      try {
        const arr = t[col]();
        if (arr && arr.length > 0) collections[col].nonEmpty++;
        else collections[col].empty++;
      } catch(e) { collections[col].error++; }
    }

    // Accessor equivalence (first 10)
    if (accessorChecks.length < 10) {
      let check = { index: i };
      try {
        const projFunc = t.project();
        const projProp = t.containingProject;
        const projFuncId = projFunc ? projFunc.id() : null;
        let projPropId = null;
        try { projPropId = projProp ? projProp.id() : null; } catch(e2) { projPropId = "ERROR"; }
        check.projectFuncId = projFuncId;
        check.projectPropId = projPropId;
        if (projFuncId === projPropId) accessorSummary.projectMatch++;
        else accessorSummary.projectDiffer++;
      } catch(e) {
        check.projectError = e.message;
        accessorSummary.projectDiffer++;
      }
      try {
        const parFunc = t.parentTask();
        const parProp = t.parent;
        const parFuncId = parFunc ? parFunc.id() : null;
        let parPropId = null;
        try { parPropId = parProp ? parProp.id() : null; } catch(e2) { parPropId = "ERROR"; }
        check.parentFuncId = parFuncId;
        check.parentPropId = parPropId;
        if (parFuncId === parPropId) accessorSummary.parentMatch++;
        else accessorSummary.parentDiffer++;
      } catch(e) {
        check.parentError = e.message;
        accessorSummary.parentDiffer++;
      }
      accessorChecks.push(check);
    }
  }

  // --- Report ---
  r += `--- Timestamp Fields ---\n`;
  r += `  added:    present=${added.present}, missing=${added.missing}\n`;
  r += `  modified: present=${modified.present}, missing=${modified.missing}\n`;

  r += `\n--- Boolean Fields ---\n`;
  r += `  active:             true=${active.true}, false=${active.false}, other=${active.other}\n`;
  r += `  effectiveActive:    true=${effActive.true}, false=${effActive.false}, other=${effActive.other}\n`;
  r += `  active↔effActive divergence: ${active.true - effActive.true} (active but not effective)\n`;
  r += `  inInbox:            true=${inInbox.true}, false=${inInbox.false}, other=${inInbox.other}\n`;
  r += `  completed:          true=${completed.true}, false=${completed.false}\n`;
  r += `  flagged:            true=${flagged.true}, false=${flagged.false}\n`;
  r += `  effectiveFlagged:   true=${effFlagged.true}, false=${effFlagged.false}\n`;
  r += `  flagged↔effFlagged divergence: ${flagDiverge}\n`;
  r += `  sequential:         true=${sequential.true}, false=${sequential.false}\n`;
  r += `  completedByChildren:true=${completedByChildren.true}, false=${completedByChildren.false}\n`;
  r += `  hasChildren:        true=${hasChildren.true}, false=${hasChildren.false}\n`;
  r += `  floatingTimeZone:   true=${floatingTZ.true}, false=${floatingTZ.false}\n`;

  r += `\n--- Status Distribution ---\n`;
  for (const [k, v] of Object.entries(statusDist).sort((a, b) => b[1] - a[1])) {
    r += `  ${k}: ${v}\n`;
  }

  r += `\n--- Relationships ---\n`;
  r += `  project:           present=${projectPresent}, null=${projectNull}\n`;
  r += `  parentTask:        present=${parentPresent}, null=${parentNull} (top-level)\n`;
  r += `  assignedContainer: present=${assignedContainerPresent}, null=${assignedContainerNull}\n`;

  r += `\n--- Date Fields ---\n`;
  for (const f of dateFields) {
    r += `  ${f}: present=${dateCounts[f].present}, missing=${dateCounts[f].missing}\n`;
  }

  r += `\n--- Other Fields ---\n`;
  r += `  name: present=${namePresent}, empty=${nameEmpty}\n`;
  r += `  estimatedMinutes: null/undefined=${estMin.null_or_undefined}, zero=${estMin.zero}, positive=${estMin.positive}\n`;
  r += `  note: non-empty=${notePresent}, empty=${noteEmpty}\n`;
  r += `  repetitionRule: present=${repRule.present}, missing=${repRule.missing}\n`;
  r += `  tags: zero=${tagCounts.zero}, one=${tagCounts.one}, multi=${tagCounts.multi}, max=${maxTags}\n`;

  r += `\n--- RepetitionRule Deep Inspection (first ${repRuleDeep.length}) ---\n`;
  if (repRuleDeep.length === 0) {
    r += `  No tasks with repetitionRule found\n`;
  } else {
    for (const d of repRuleDeep) {
      r += `  Task "${d.name}" (index ${d.index}):\n`;
      r += `    ruleString: [${d.ruleStringType}] ${d.ruleString}\n`;
      r += `    scheduleType: [${d.scheduleTypeType}] ${d.scheduleType}\n`;
      r += `    fixedInterval: [${d.fixedIntervalType}] ${d.fixedInterval}\n`;
      r += `    unit: [${d.unitType}] ${d.unit}\n`;
    }
  }

  r += `\n--- Collections ---\n`;
  for (const col of ["linkedFileURLs", "notifications", "attachments"]) {
    const c = collections[col];
    r += `  ${col}: nonEmpty=${c.nonEmpty}, empty=${c.empty}, error=${c.error}\n`;
  }

  r += `\n--- Accessor Equivalence (first 10) ---\n`;
  r += `  project() vs containingProject: match=${accessorSummary.projectMatch}, differ=${accessorSummary.projectDiffer}\n`;
  r += `  parentTask() vs parent:         match=${accessorSummary.parentMatch}, differ=${accessorSummary.parentDiffer}\n`;
  if (accessorChecks.length > 0) {
    r += `  Sample details:\n`;
    for (const c of accessorChecks.slice(0, 3)) {
      r += `    [${c.index}] project: func=${c.projectFuncId}, prop=${c.projectPropId}`;
      if (c.projectError) r += ` ERROR=${c.projectError}`;
      r += ` | parent: func=${c.parentFuncId}, prop=${c.parentPropId}`;
      if (c.parentError) r += ` ERROR=${c.parentError}`;
      r += `\n`;
    }
  }

  return r;
})();
