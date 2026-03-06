// 12 — Perspective Audit
// READ-ONLY — no modifications to OmniFocus data
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Scans ALL perspectives via multiple access paths.
// Covers: Perspective.all vs BuiltIn/Custom split, identifier (null for builtin
// vs present for custom), name, and probes for any additional accessible properties.

(() => {
  let r = `=== 12: Perspective Audit ===\n\n`;

  // --- Access Path Comparison ---
  r += `--- Access Paths ---\n`;

  let perspAll = null, perspBuiltIn = null, perspCustom = null;

  // Try Perspective.all (used by bridge.js)
  try {
    perspAll = Perspective.all;
    r += `  Perspective.all count: ${perspAll.length}\n`;
  } catch(e) {
    r += `  Perspective.all: ERROR — ${e.message}\n`;
  }

  // Try Perspective.BuiltIn.all + Perspective.Custom.all
  try {
    perspBuiltIn = Perspective.BuiltIn.all;
    r += `  Perspective.BuiltIn.all count: ${perspBuiltIn.length}\n`;
  } catch(e) {
    r += `  Perspective.BuiltIn.all: ERROR — ${e.message}\n`;
  }

  try {
    perspCustom = Perspective.Custom.all;
    r += `  Perspective.Custom.all count: ${perspCustom.length}\n`;
  } catch(e) {
    r += `  Perspective.Custom.all: ERROR — ${e.message}\n`;
  }

  if (perspBuiltIn && perspCustom) {
    r += `  BuiltIn + Custom total: ${perspBuiltIn.length + perspCustom.length}\n`;
    if (perspAll) {
      r += `  Matches Perspective.all: ${perspAll.length === perspBuiltIn.length + perspCustom.length}\n`;
    }
  }
  r += `\n`;

  // Use whichever is available — prefer Perspective.all, fallback to BuiltIn+Custom concat
  let perspectives;
  if (perspAll) {
    perspectives = perspAll;
    r += `Using: Perspective.all\n\n`;
  } else if (perspBuiltIn && perspCustom) {
    perspectives = perspBuiltIn.concat(perspCustom);
    r += `Using: Perspective.BuiltIn.all + Perspective.Custom.all (concatenated)\n\n`;
  } else if (perspCustom) {
    perspectives = perspCustom;
    r += `Using: Perspective.Custom.all only (BuiltIn failed)\n\n`;
  } else {
    return r + `ERROR: All access paths failed\n`;
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
      ident = persp.identifier;
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
      name = persp.name;
      if (name && name.length > 0) namePresent++; else nameMissing++;
    } catch(e) {
      nameMissing++;
      name = "(error)";
    }

    // Classify
    if (ident && ident.length > 0) {
      customList.push({ name: name, id: ident });
    } else {
      builtinList.push({ name: name });
    }

    // Probe additional fields
    for (const f of probeFields) {
      try {
        const val = persp[f];
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
        const val = sample[f];
        r += `  ${f}: ${val !== undefined ? `accessible (=${typeof val === "string" ? `"${val}"` : val})` : "undefined"}\n`;
      } catch(e) {
        r += `  ${f}: not a property\n`;
      }
    }
  }

  return r;
})();
