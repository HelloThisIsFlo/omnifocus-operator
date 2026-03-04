// 12 — Perspective Audit
// READ-ONLY — no modifications to OmniFocus data
//
// Scans ALL perspectives (Perspective.all).
// Covers: identifier (null for builtin vs present for custom), name,
// and probes for any additional accessible properties.

(() => {
  const app = Application("OmniFocus");
  const doc = app.defaultDocument;

  let r = `=== 12: Perspective Audit ===\n\n`;

  // Get all perspectives
  let perspectives;
  try {
    perspectives = doc.perspectives();
    r += `Total perspectives: ${perspectives.length}\n\n`;
  } catch(e) {
    return r + `ERROR getting perspectives: ${e.message}\n`;
  }

  // --- Counters ---
  let identifierPresent = 0, identifierNull = 0;
  let namePresent = 0, nameMissing = 0;
  let builtinTrue = 0, builtinFalse = 0, builtinUndef = 0;

  // Track all perspectives for listing
  let builtinList = [];
  let customList = [];

  // Probe for additional properties
  let probeResults = {};
  const probeFields = ["added", "modified", "active", "effectiveActive", "status",
                       "note", "parent", "completed", "flagged"];
  for (const f of probeFields) probeResults[f] = { exists: 0, missing: 0, error: 0 };

  for (let i = 0; i < perspectives.length; i++) {
    const persp = perspectives[i];

    // identifier
    let ident;
    try {
      ident = persp.identifier();
      if (ident && ident.length > 0) {
        identifierPresent++;
      } else {
        identifierNull++;
      }
    } catch(e) {
      identifierNull++;
      ident = null;
    }

    // name
    let name;
    try {
      name = persp.name();
      if (name && name.length > 0) namePresent++; else nameMissing++;
    } catch(e) {
      nameMissing++;
      name = "(error)";
    }

    // builtin — try the property, it may not exist
    try {
      const b = persp.id();  // built-in perspectives might use id differently
      // We'll classify by identifier presence instead
    } catch(e) {}

    // Classify
    if (ident && ident.length > 0) {
      customList.push({ name: name, id: ident });
    } else {
      builtinList.push({ name: name });
    }

    // Probe additional fields
    for (const f of probeFields) {
      try {
        const val = persp[f]();
        if (val !== undefined) probeResults[f].exists++;
        else probeResults[f].missing++;
      } catch(e) {
        probeResults[f].error++;
      }
    }
  }

  // --- Report ---
  r += `--- Core Fields ---\n`;
  r += `  identifier: present=${identifierPresent} (custom), null/empty=${identifierNull} (builtin)\n`;
  r += `  name: present=${namePresent}, missing=${nameMissing}\n`;

  r += `\n--- Built-in Perspectives (no identifier) ---\n`;
  for (const p of builtinList) {
    r += `  "${p.name}"\n`;
  }

  r += `\n--- Custom Perspectives (have identifier) ---\n`;
  for (const p of customList) {
    r += `  "${p.name}" (id: ${p.id})\n`;
  }

  r += `\n--- Property Probes ---\n`;
  r += `  Testing which standard properties exist on Perspective objects:\n`;
  for (const f of probeFields) {
    const pr = probeResults[f];
    if (pr.exists > 0) {
      r += `  ✅ ${f}: accessible (${pr.exists} have values)\n`;
    } else if (pr.error > 0) {
      r += `  ❌ ${f}: not a property (${pr.error} errors)\n`;
    } else {
      r += `  ⚪ ${f}: accessible but always undefined/null\n`;
    }
  }

  // --- Try to discover Perspective-specific properties ---
  r += `\n--- Perspective-Specific Property Probe ---\n`;
  if (perspectives.length > 0) {
    const sample = perspectives[0];
    const extraFields = ["fileURL", "color", "iconName", "window", "originalIconName",
                         "sidebar", "contents", "filter", "focus", "grouping",
                         "sorting", "layout", "containerType", "customFilterFormula"];
    for (const f of extraFields) {
      try {
        const val = sample[f]();
        r += `  ${f}: ${val !== undefined ? `accessible (=${typeof val === "string" ? `"${val}"` : val})` : "undefined"}\n`;
      } catch(e) {
        r += `  ${f}: not a property\n`;
      }
    }
  }

  return r;
})();
