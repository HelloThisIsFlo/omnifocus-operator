// 15 — Tag Hierarchy Inheritance
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Checks whether tag status (OnHold/Dropped) propagates to child tags
// through active/effectiveActive, similar to how folder status propagates
// to projects.

(() => {
  let r = `=== 15: Tag Hierarchy Inheritance ===\n\n`;

  function resolveTagStatus(tag) {
    if (tag.status === Tag.Status.Active) return "Active";
    if (tag.status === Tag.Status.OnHold) return "OnHold";
    if (tag.status === Tag.Status.Dropped) return "Dropped";
    return "UNKNOWN";
  }

  const allTags = flattenedTags;
  r += `Total tags: ${allTags.length}\n\n`;

  // --- Map parent-child relationships ---
  let topLevel = 0;
  let nested = 0;
  for (let i = 0; i < allTags.length; i++) {
    if (allTags[i].parent) nested++;
    else topLevel++;
  }
  r += `Top-level tags: ${topLevel}\n`;
  r += `Nested tags: ${nested}\n\n`;

  // --- Find non-Active tags ---
  const specialTags = [];
  for (let i = 0; i < allTags.length; i++) {
    const tag = allTags[i];
    const status = resolveTagStatus(tag);
    if (status !== "Active") {
      specialTags.push({ tag: tag, status: status });
    }
  }

  r += `--- Non-Active Tags ---\n`;
  if (specialTags.length === 0) {
    r += `  None found — all tags are Active.\n`;
    r += `  Cannot test hierarchy inheritance without OnHold/Dropped parent tags.\n`;
    return r;
  }

  for (let i = 0; i < specialTags.length; i++) {
    const entry = specialTags[i];
    const tag = entry.tag;
    r += `\n  "${tag.name}" | status=${entry.status}`;
    r += ` | active=${tag.active} | effActive=${tag.effectiveActive}`;
    r += ` | allowsNextAction=${tag.allowsNextAction}`;
    if (tag.parent) {
      r += ` | parent="${tag.parent.name}" (${resolveTagStatus(tag.parent)})`;
    } else {
      r += ` | parent=null (top-level)`;
    }
    r += `\n`;

    // Check children
    const children = tag.tags;
    if (children.length > 0) {
      r += `    Children (${children.length}):\n`;
      for (let j = 0; j < children.length; j++) {
        const child = children[j];
        r += `      "${child.name}" | status=${resolveTagStatus(child)}`;
        r += ` | active=${child.active} | effActive=${child.effectiveActive}`;
        r += ` | allowsNextAction=${child.allowsNextAction}\n`;
      }
    } else {
      r += `    No children\n`;
    }
  }

  // --- Check ALL nested tags for inheritance patterns ---
  r += `\n--- Full Inheritance Check (tags with non-Active parents) ---\n`;
  let inheritanceCount = 0;
  for (let i = 0; i < allTags.length; i++) {
    const tag = allTags[i];
    if (!tag.parent) continue;

    const parentStatus = resolveTagStatus(tag.parent);
    if (parentStatus !== "Active" || !tag.parent.effectiveActive) {
      inheritanceCount++;
      r += `  "${tag.name}" (${resolveTagStatus(tag)}, active=${tag.active}, effActive=${tag.effectiveActive})`;
      r += ` inside "${tag.parent.name}" (${parentStatus}, active=${tag.parent.active}, effActive=${tag.parent.effectiveActive})\n`;
    }
  }
  if (inheritanceCount === 0) {
    r += `  No tags with non-Active parents found.\n`;
    r += `  All OnHold/Dropped tags are top-level or inside Active parents.\n`;
  } else {
    r += `  Found ${inheritanceCount} tags inside non-Active parents.\n`;
  }

  // --- Also check: do Active tags inside OnHold parents have effectiveActive=false? ---
  r += `\n--- Key Question: Does effectiveActive propagate through tag hierarchy? ---\n`;
  let activeInNonActive = 0;
  let activeInNonActiveEffFalse = 0;
  for (let i = 0; i < allTags.length; i++) {
    const tag = allTags[i];
    if (!tag.parent) continue;
    if (resolveTagStatus(tag) === "Active" && resolveTagStatus(tag.parent) !== "Active") {
      activeInNonActive++;
      if (!tag.effectiveActive) activeInNonActiveEffFalse++;
    }
  }
  r += `Active tags inside non-Active parents: ${activeInNonActive}\n`;
  r += `  Of those, effectiveActive=false: ${activeInNonActiveEffFalse}\n`;
  if (activeInNonActive > 0) {
    if (activeInNonActiveEffFalse === activeInNonActive) {
      r += `  → YES, effectiveActive propagates (all inherit false from parent)\n`;
    } else if (activeInNonActiveEffFalse === 0) {
      r += `  → NO, effectiveActive does NOT propagate (all remain true)\n`;
    } else {
      r += `  → MIXED — some propagate, some don't\n`;
    }
  } else {
    r += `  → No test cases available in this DB\n`;
  }

  return r;
})();
