// 11 — Folder Audit
// READ-ONLY — no modifications to OmniFocus data
//
// Scans ALL flattenedFolders with counter-based approach.
// Covers: added/modified, active/effectiveActive, status distribution,
// status enum matching, parent relationships.

(() => {
  const app = Application("OmniFocus");
  const doc = app.defaultDocument;
  const folders = doc.flattenedFolders();
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

  let hasName = 0, nameMissing = 0;
  let notePresent = 0, noteEmpty = 0;

  for (let i = 0; i < total; i++) {
    const folder = folders[i];

    // added/modified
    const a = folder.added();
    const m = folder.modified();
    if (a instanceof Date) added.present++; else added.missing++;
    if (m instanceof Date) modified.present++; else modified.missing++;

    // active/effectiveActive
    const act = folder.active();
    if (act === true) active.true++; else if (act === false) active.false++; else active.other++;
    const ea = folder.effectiveActive();
    if (ea === true) effActive.true++; else if (ea === false) effActive.false++; else effActive.other++;

    // status
    const s = matchFolderStatus(folder.status());
    statusDist[s] = (statusDist[s] || 0) + 1;

    // parent
    try {
      const par = folder.parent();
      // Folder.parent might return the document for top-level folders
      // Check if it's actually a folder
      if (par && par.class && par.class() === "folder") {
        parentPresent++;
      } else {
        parentNull++;
      }
    } catch(e) { parentNull++; }

    // name
    const n = folder.name();
    if (n && n.length > 0) hasName++; else nameMissing++;

    // note (check if folders have notes)
    try {
      const note = folder.note();
      if (note && note.length > 0) notePresent++; else noteEmpty++;
    } catch(e) { noteEmpty++; }
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

  r += `\n--- Relationships ---\n`;
  r += `  parent: present=${parentPresent} (nested), null=${parentNull} (top-level)\n`;

  r += `\n--- Other Fields ---\n`;
  r += `  name: present=${hasName}, missing=${nameMissing}\n`;
  r += `  note: non-empty=${notePresent}, empty=${noteEmpty}\n`;

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
