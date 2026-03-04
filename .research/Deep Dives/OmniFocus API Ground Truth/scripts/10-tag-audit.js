// 10 — Tag Audit
// READ-ONLY — no modifications to OmniFocus data
//
// Scans ALL flattenedTags with counter-based approach.
// Covers: added/modified, active/effectiveActive, status distribution,
// status enum matching, allowsNextAction, parent relationships.

(() => {
  const app = Application("OmniFocus");
  const doc = app.defaultDocument;
  const tags = doc.flattenedTags();
  const total = tags.length;

  let r = `=== 10: Tag Audit ===\n`;
  r += `Total tags: ${total}\n\n`;

  // --- Counters ---
  let added = { present: 0, missing: 0 };
  let modified = { present: 0, missing: 0 };
  let active = { true: 0, false: 0, other: 0 };
  let effActive = { true: 0, false: 0, other: 0 };
  let allowsNextAction = { true: 0, false: 0, other: 0 };
  let parentPresent = 0, parentNull = 0;
  let childrenZero = 0, childrenNonZero = 0;

  // Status distribution via === matching
  function matchTagStatus(val) {
    if (val === null || val === undefined) return "null";
    try { if (val === Tag.Status.Active) return "Active"; } catch(e) {}
    try { if (val === Tag.Status.OnHold) return "OnHold"; } catch(e) {}
    try { if (val === Tag.Status.Dropped) return "Dropped"; } catch(e) {}
    return "UNKNOWN";
  }
  let statusDist = {};

  // Note presence (3 categories)
  let noteNullUndef = 0, noteEmptyStr = 0, noteNonEmpty = 0;

  // id presence
  let idPresent = 0, idMissing = 0;

  // Also try accessing other properties that might exist
  let hasName = 0, nameMissing = 0;

  for (let i = 0; i < total; i++) {
    const tag = tags[i];

    // id
    try {
      const tid = tag.id();
      if (tid && tid.length > 0) idPresent++; else idMissing++;
    } catch(e) { idMissing++; }

    // added/modified
    const a = tag.added();
    const m = tag.modified();
    if (a instanceof Date) added.present++; else added.missing++;
    if (m instanceof Date) modified.present++; else modified.missing++;

    // active/effectiveActive
    const act = tag.active();
    if (act === true) active.true++; else if (act === false) active.false++; else active.other++;
    const ea = tag.effectiveActive();
    if (ea === true) effActive.true++; else if (ea === false) effActive.false++; else effActive.other++;

    // status
    const s = matchTagStatus(tag.status());
    statusDist[s] = (statusDist[s] || 0) + 1;

    // allowsNextAction
    const ana = tag.allowsNextAction();
    if (ana === true) allowsNextAction.true++;
    else if (ana === false) allowsNextAction.false++;
    else allowsNextAction.other++;

    // parent
    try {
      const par = tag.parent();
      if (par) parentPresent++; else parentNull++;
    } catch(e) { parentNull++; }

    // children (tag.tags())
    try {
      if (tag.tags().length > 0) childrenNonZero++;
      else childrenZero++;
    } catch(e) { childrenZero++; }

    // name
    const n = tag.name();
    if (n && n.length > 0) hasName++; else nameMissing++;

    // note (3 categories: null/undefined, empty string, non-empty)
    try {
      const note = tag.note();
      if (note === null || note === undefined) noteNullUndef++;
      else if (note.length === 0) noteEmptyStr++;
      else noteNonEmpty++;
    } catch(e) { noteNullUndef++; }
  }

  // --- Name Uniqueness Check ---
  let nameCountMap = {};
  for (let i = 0; i < total; i++) {
    const n = tags[i].name();
    if (n) nameCountMap[n] = (nameCountMap[n] || 0) + 1;
  }
  const uniqueNames = Object.keys(nameCountMap).length;
  let duplicateNames = [];
  for (const [name, count] of Object.entries(nameCountMap)) {
    if (count > 1) duplicateNames.push({ name, count });
  }

  // --- Report ---
  r += `--- Timestamp Fields ---\n`;
  r += `  added:    present=${added.present}, missing=${added.missing}\n`;
  r += `  modified: present=${modified.present}, missing=${modified.missing}\n`;

  r += `\n--- Boolean Fields ---\n`;
  r += `  active:             true=${active.true}, false=${active.false}, other=${active.other}\n`;
  r += `  effectiveActive:    true=${effActive.true}, false=${effActive.false}, other=${effActive.other}\n`;
  r += `  active↔effActive divergence: ${active.true - effActive.true}\n`;
  r += `  allowsNextAction:   true=${allowsNextAction.true}, false=${allowsNextAction.false}, other=${allowsNextAction.other}\n`;

  r += `\n--- Status Distribution (=== match) ---\n`;
  for (const [k, v] of Object.entries(statusDist).sort((a, b) => b[1] - a[1])) {
    r += `  ${k}: ${v}\n`;
  }

  const statusSum = Object.values(statusDist).reduce((a, b) => a + b, 0);
  r += `  Sum check: ${statusSum}/${total} ${statusSum === total ? "✅" : "❌ MISMATCH"}\n`;

  r += `\n--- Relationships ---\n`;
  r += `  parent: present=${parentPresent} (nested), null=${parentNull} (top-level)\n`;
  r += `  children (tag.tags()): hasChildren=${childrenNonZero}, leaf=${childrenZero}\n`;

  r += `\n--- Other Fields ---\n`;
  r += `  id: present=${idPresent}, missing=${idMissing}\n`;
  r += `  name: present=${hasName}, missing=${nameMissing}\n`;
  r += `  note: null/undefined=${noteNullUndef}, empty_string=${noteEmptyStr}, non_empty=${noteNonEmpty}\n`;

  r += `\n--- Name Uniqueness ---\n`;
  r += `  Total tags: ${total}, unique names: ${uniqueNames}\n`;
  if (duplicateNames.length === 0) {
    r += `  ✅ All tag names are unique\n`;
  } else {
    r += `  ⚠️ Duplicate names found: ${duplicateNames.length}\n`;
    for (const d of duplicateNames.slice(0, 10)) {
      r += `    "${d.name}": ${d.count} occurrences\n`;
    }
    if (duplicateNames.length > 10) r += `    ... and ${duplicateNames.length - 10} more\n`;
  }

  // --- Status enum comparison with Project.Status ---
  r += `\n--- Tag.Status Constants ---\n`;
  const tagConstants = ["Active", "OnHold", "Dropped", "Done", "Blocked", "Available"];
  for (const c of tagConstants) {
    try {
      const val = Tag.Status[c];
      r += `  Tag.Status.${c}: ${val !== undefined ? "EXISTS" : "undefined"}\n`;
    } catch(e) {
      r += `  Tag.Status.${c}: NOT FOUND\n`;
    }
  }

  // Cross-reference with Project.Status
  r += `\n--- Cross-Type Comparison ---\n`;
  try {
    r += `  Tag.Status.Active === Project.Status.Active: ${Tag.Status.Active === Project.Status.Active}\n`;
  } catch(e) { r += `  Tag.Status.Active === Project.Status.Active: ERROR\n`; }
  try {
    r += `  Tag.Status.OnHold === Project.Status.OnHold: ${Tag.Status.OnHold === Project.Status.OnHold}\n`;
  } catch(e) { r += `  Tag.Status.OnHold === Project.Status.OnHold: ERROR\n`; }
  try {
    r += `  Tag.Status.Dropped === Project.Status.Dropped: ${Tag.Status.Dropped === Project.Status.Dropped}\n`;
  } catch(e) { r += `  Tag.Status.Dropped === Project.Status.Dropped: ERROR\n`; }

  return r;
})();
