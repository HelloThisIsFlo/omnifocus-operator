// 17 — Perspective Mismatch Investigation
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Investigates why Perspective.all (57) doesn't match
// BuiltIn.all + Custom.all (8 + 50 = 58).
// Identifies which perspective(s) differ between the collections.

(() => {
  let r = `=== 17: Perspective Mismatch Investigation ===\n\n`;

  const all = Perspective.all;
  const builtIn = Perspective.BuiltIn.all;
  const custom = Perspective.Custom.all;

  r += `Perspective.all: ${all.length}\n`;
  r += `BuiltIn.all: ${builtIn.length}\n`;
  r += `Custom.all: ${custom.length}\n`;
  r += `BuiltIn + Custom: ${builtIn.length + custom.length}\n`;
  r += `Match: ${all.length === builtIn.length + custom.length}\n\n`;

  // Helper: get a stable key for a perspective (id.primaryKey if available, else name)
  function pKey(p) {
    try { return p.id.primaryKey; } catch(e) { return "NAME:" + p.name; }
  }

  // Build ID lookup from Perspective.all
  const allIds = {};
  for (let i = 0; i < all.length; i++) {
    const k = pKey(all[i]);
    allIds[k] = all[i];
  }

  // Check BuiltIn perspectives
  r += `--- BuiltIn Perspectives ---\n`;
  for (let i = 0; i < builtIn.length; i++) {
    const p = builtIn[i];
    const k = pKey(p);
    const inAll = allIds[k] ? "in .all" : "NOT in .all";
    const hasId = p.identifier ? p.identifier : "(no identifier)";
    const idStr = (p.id !== undefined) ? k : "(no id)";
    r += `  "${p.name}" | id=${idStr} | identifier=${hasId} | ${inAll}\n`;
  }

  // Check Custom perspectives
  r += `\n--- Custom Perspectives NOT in Perspective.all ---\n`;
  let customMissing = 0;
  for (let i = 0; i < custom.length; i++) {
    const p = custom[i];
    if (!allIds[pKey(p)]) {
      customMissing++;
      r += `  "${p.name}" | id=${pKey(p)} | identifier=${p.identifier}\n`;
    }
  }
  if (customMissing === 0) {
    r += `  All custom perspectives found in Perspective.all ✅\n`;
  }

  // Check for perspectives in .all but not in BuiltIn or Custom
  r += `\n--- Perspectives in .all but not in BuiltIn or Custom ---\n`;
  const builtInIds = {};
  for (let i = 0; i < builtIn.length; i++) {
    builtInIds[pKey(builtIn[i])] = true;
  }
  const customIds = {};
  for (let i = 0; i < custom.length; i++) {
    customIds[pKey(custom[i])] = true;
  }
  let orphans = 0;
  for (let i = 0; i < all.length; i++) {
    const p = all[i];
    const k = pKey(p);
    if (!builtInIds[k] && !customIds[k]) {
      orphans++;
      r += `  "${p.name}" | id=${k}\n`;
    }
  }
  if (orphans === 0) {
    r += `  None — all Perspective.all entries are accounted for.\n`;
  }

  return r;
})();
