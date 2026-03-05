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

  // Build ID lookup from Perspective.all
  const allIds = {};
  for (let i = 0; i < all.length; i++) {
    allIds[all[i].id.primaryKey] = all[i];
  }

  // Check BuiltIn perspectives
  r += `--- BuiltIn Perspectives ---\n`;
  for (let i = 0; i < builtIn.length; i++) {
    const p = builtIn[i];
    const inAll = allIds[p.id.primaryKey] ? "in .all" : "NOT in .all";
    const hasId = p.identifier ? p.identifier : "(no identifier)";
    r += `  "${p.name}" | id=${p.id.primaryKey} | identifier=${hasId} | ${inAll}\n`;
  }

  // Check Custom perspectives
  r += `\n--- Custom Perspectives NOT in Perspective.all ---\n`;
  let customMissing = 0;
  for (let i = 0; i < custom.length; i++) {
    const p = custom[i];
    if (!allIds[p.id.primaryKey]) {
      customMissing++;
      r += `  "${p.name}" | id=${p.id.primaryKey} | identifier=${p.identifier}\n`;
    }
  }
  if (customMissing === 0) {
    r += `  All custom perspectives found in Perspective.all ✅\n`;
  }

  // Check for perspectives in .all but not in BuiltIn or Custom
  r += `\n--- Perspectives in .all but not in BuiltIn or Custom ---\n`;
  const builtInIds = {};
  for (let i = 0; i < builtIn.length; i++) {
    builtInIds[builtIn[i].id.primaryKey] = true;
  }
  const customIds = {};
  for (let i = 0; i < custom.length; i++) {
    customIds[custom[i].id.primaryKey] = true;
  }
  let orphans = 0;
  for (let i = 0; i < all.length; i++) {
    const p = all[i];
    if (!builtInIds[p.id.primaryKey] && !customIds[p.id.primaryKey]) {
      orphans++;
      r += `  "${p.name}" | id=${p.id.primaryKey}\n`;
    }
  }
  if (orphans === 0) {
    r += `  None — all Perspective.all entries are accounted for.\n`;
  }

  return r;
})();
