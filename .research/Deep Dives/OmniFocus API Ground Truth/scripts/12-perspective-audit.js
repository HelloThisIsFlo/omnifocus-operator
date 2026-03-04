// 12 — Perspective Audit
// READ-ONLY — no modifications to OmniFocus data
//
// Scans ALL perspectives via both access paths (Perspective.all and doc.perspectives()).
// Covers: dual access path comparison, identifier (null for builtin vs present for
// custom), name, and probes for any additional accessible properties.

(() => {
  const app = Application("OmniFocus");
  const doc = app.defaultDocument;

  let r = `=== 12: Perspective Audit ===\n\n`;

  // --- Dual Access Path Comparison ---
  r += `--- Access Paths ---\n`;
  let perspAll = null, perspDoc = null;
  try {
    perspAll = Perspective.all;
    r += `  Perspective.all count: ${perspAll.length}\n`;
  } catch(e) {
    r += `  Perspective.all: ERROR — ${e.message}\n`;
  }
  try {
    perspDoc = doc.perspectives();
    r += `  doc.perspectives() count: ${perspDoc.length}\n`;
  } catch(e) {
    r += `  doc.perspectives(): ERROR — ${e.message}\n`;
  }
  if (perspAll && perspDoc) {
    r += `  Counts match: ${perspAll.length === perspDoc.length}\n`;
  }
  r += `\n`;

  // Use whichever is more complete, prefer perspAll, fallback to perspDoc
  let perspectives;
  if (perspAll && perspDoc) {
    perspectives = perspAll.length >= perspDoc.length ? perspAll : perspDoc;
    r += `Using: ${perspAll.length >= perspDoc.length ? "Perspective.all" : "doc.perspectives()"}\n\n`;
  } else if (perspAll) {
    perspectives = perspAll;
    r += `Using: Perspective.all (doc.perspectives() failed)\n\n`;
  } else if (perspDoc) {
    perspectives = perspDoc;
    r += `Using: doc.perspectives() (Perspective.all failed)\n\n`;
  } else {
    return r + `ERROR: Both access paths failed\n`;
  }

  r += `Total perspectives: ${perspectives.length}\n\n`;

  // --- Counters ---
  let identifierPresent = 0, identifierNull = 0;
  let namePresent = 0, nameMissing = 0;
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
  const identSum = identifierPresent + identifierNull;
  r += `  Sum check: ${identSum}/${perspectives.length} ${identSum === perspectives.length ? "✅" : "❌ MISMATCH"}\n`;
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
