// 11 — Folder Audit
// READ-ONLY — no modifications to OmniFocus data
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Scans ALL flattenedFolders with counter-based approach.
// Covers: added/modified, active/effectiveActive, status distribution,
// status enum matching, parent relationships.

(() => {
  const folders = flattenedFolders;
  const total = folders.length;

  let r = `=== 11: Folder Audit ===\n`;
  r += `Total folders: ${total}\n\n`;

  // --- Counters ---
  let added = { present: 0, missing: 0 };
  let modified = { present: 0, missing: 0 };
  let active = { true: 0, false: 0, other: 0 };
  let effActive = { true: 0, false: 0, other: 0 };
  let parentPresent = 0, parentNull = 0;

  // Status distribution via === matching
  function matchFolderStatus(val) {
    if (val === null || val === undefined) return "null";
    try { if (val === Folder.Status.Active) return "Active"; } catch(e) {}
    try { if (val === Folder.Status.Dropped) return "Dropped"; } catch(e) {}
    // Try other possibilities
    try { if (val === Folder.Status.OnHold) return "OnHold"; } catch(e) {}
    try { if (val === Folder.Status.Done) return "Done"; } catch(e) {}
    return "UNKNOWN";
  }
  let statusDist = {};

  // id presence
  let idPresent = 0, idMissing = 0;

  let hasName = 0, nameMissing = 0;
  let noteNullUndef = 0, noteEmptyStr = 0, noteNonEmpty = 0;

  // Hierarchy probing
  let projectsTotal = 0, subfoldersTotal = 0;
  let hasProjects = 0, hasSubfolders = 0;

  for (let i = 0; i < total; i++) {
    const folder = folders[i];

    // id
    try {
      const fid = folder.id.primaryKey;
      if (fid && fid.length > 0) idPresent++; else idMissing++;
    } catch(e) { idMissing++; }

    // added/modified
    const a = folder.added;
    const m = folder.modified;
    if (a instanceof Date) added.present++; else added.missing++;
    if (m instanceof Date) modified.present++; else modified.missing++;

    // active/effectiveActive
    const act = folder.active;
    if (act === true) active.true++; else if (act === false) active.false++; else active.other++;
    const ea = folder.effectiveActive;
    if (ea === true) effActive.true++; else if (ea === false) effActive.false++; else effActive.other++;

    // status
    const s = matchFolderStatus(folder.status);
    statusDist[s] = (statusDist[s] || 0) + 1;

    // parent — use instanceof to check type instead of .class()
    try {
      const par = folder.parent;
      if (par && par instanceof Folder) {
        parentPresent++;
      } else {
        parentNull++;
      }
    } catch(e) { parentNull++; }

    // name
    const n = folder.name;
    if (n && n.length > 0) hasName++; else nameMissing++;

    // note (3 categories: null/undefined, empty string, non-empty)
    try {
      const note = folder.note;
      if (note === null || note === undefined) noteNullUndef++;
      else if (note.length === 0) noteEmptyStr++;
      else noteNonEmpty++;
    } catch(e) { noteNullUndef++; }

    // hierarchy: projects and subfolders
    try {
      const pc = folder.projects.length;
      projectsTotal += pc;
      if (pc > 0) hasProjects++;
    } catch(e) {}
    try {
      const sc = folder.folders.length;
      subfoldersTotal += sc;
      if (sc > 0) hasSubfolders++;
    } catch(e) {}
  }

  // --- Report ---
  r += `--- Timestamp Fields ---\n`;
  r += `  added:    present=${added.present}, missing=${added.missing}\n`;
  r += `  modified: present=${modified.present}, missing=${modified.missing}\n`;

  r += `\n--- Boolean Fields ---\n`;
  r += `  active:             true=${active.true}, false=${active.false}, other=${active.other}\n`;
  r += `  effectiveActive:    true=${effActive.true}, false=${effActive.false}, other=${effActive.other}\n`;
  r += `  active↔effActive divergence: ${active.true - effActive.true}\n`;

  r += `\n--- Status Distribution (=== match) ---\n`;
  for (const [k, v] of Object.entries(statusDist).sort((a, b) => b[1] - a[1])) {
    r += `  ${k}: ${v}\n`;
  }

  const statusSum = Object.values(statusDist).reduce((a, b) => a + b, 0);
  r += `  Sum check: ${statusSum}/${total} ${statusSum === total ? "✅" : "❌ MISMATCH"}\n`;

  r += `\n--- Relationships ---\n`;
  r += `  parent: present=${parentPresent} (nested), null=${parentNull} (top-level)\n`;

  r += `\n--- Other Fields ---\n`;
  r += `  id: present=${idPresent}, missing=${idMissing}\n`;
  r += `  name: present=${hasName}, missing=${nameMissing}\n`;
  r += `  note: null/undefined=${noteNullUndef}, empty_string=${noteEmptyStr}, non_empty=${noteNonEmpty}\n`;

  r += `\n--- Hierarchy ---\n`;
  r += `  folders with projects: ${hasProjects}/${total}, total projects: ${projectsTotal}\n`;
  r += `  folders with subfolders: ${hasSubfolders}/${total}, total subfolders: ${subfoldersTotal}\n`;

  // --- Folder.Status Constants ---
  r += `\n--- Folder.Status Constants ---\n`;
  const folderConstants = ["Active", "Dropped", "OnHold", "Done", "Blocked", "Available"];
  for (const c of folderConstants) {
    try {
      const val = Folder.Status[c];
      r += `  Folder.Status.${c}: ${val !== undefined ? "EXISTS" : "undefined"}\n`;
    } catch(e) {
      r += `  Folder.Status.${c}: NOT FOUND\n`;
    }
  }

  // Cross-reference with Project.Status
  r += `\n--- Cross-Type Comparison ---\n`;
  try {
    r += `  Folder.Status.Active === Project.Status.Active: ${Folder.Status.Active === Project.Status.Active}\n`;
  } catch(e) { r += `  Folder.Status.Active === Project.Status.Active: ERROR\n`; }
  try {
    r += `  Folder.Status.Dropped === Project.Status.Dropped: ${Folder.Status.Dropped === Project.Status.Dropped}\n`;
  } catch(e) { r += `  Folder.Status.Dropped === Project.Status.Dropped: ERROR\n`; }
  try {
    r += `  Folder.Status.Active === Tag.Status.Active: ${Folder.Status.Active === Tag.Status.Active}\n`;
  } catch(e) { r += `  Folder.Status.Active === Tag.Status.Active: ERROR\n`; }

  return r;
})();
