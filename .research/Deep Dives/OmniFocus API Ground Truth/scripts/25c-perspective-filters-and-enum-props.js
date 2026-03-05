// 25c — Perspective Filter Config & Enum Extra Props
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Part 1: Reads archivedFilterRules, archivedTopLevelFilterAggregation,
//         and iconColor on all perspectives.
// Part 2: Enumerates all properties on every enum object to see what
//         exists beyond the known constants.

(() => {
  let r = `=== 25c: Perspective Filters & Enum Props ===\n\n`;

  // =============================================
  // PART 1: Perspective filter config
  // =============================================
  r += `=== PART 1: Perspective Filter Config ===\n\n`;

  const perspectives = Perspective.all;
  r += `Total perspectives: ${perspectives.length}\n\n`;

  for (let i = 0; i < perspectives.length; i++) {
    const p = perspectives[i];
    r += `--- "${p.name}" (${p.identifier ? p.identifier : "built-in"}) ---\n`;

    // archivedFilterRules
    try {
      const rules = p.archivedFilterRules;
      if (rules === undefined) {
        r += `  archivedFilterRules: undefined\n`;
      } else if (rules === null) {
        r += `  archivedFilterRules: null\n`;
      } else if (Array.isArray(rules)) {
        r += `  archivedFilterRules: Array(${rules.length})\n`;
        for (let j = 0; j < rules.length; j++) {
          try {
            // Try to see what each rule looks like
            const rule = rules[j];
            const type = typeof rule;
            if (type === "object" && rule !== null) {
              const keys = Object.getOwnPropertyNames(rule);
              r += `    [${j}]: object with ${keys.length} props: ${keys.join(", ")}\n`;
              // Print each property value
              for (let k = 0; k < keys.length; k++) {
                try {
                  const val = rule[keys[k]];
                  const valType = typeof val;
                  if (valType === "string" || valType === "number" || valType === "boolean") {
                    r += `      ${keys[k]}: ${JSON.stringify(val)}\n`;
                  } else if (val === null) {
                    r += `      ${keys[k]}: null\n`;
                  } else if (val === undefined) {
                    r += `      ${keys[k]}: undefined\n`;
                  } else if (Array.isArray(val)) {
                    r += `      ${keys[k]}: Array(${val.length})\n`;
                    // Print array items if they're simple
                    for (let m = 0; m < val.length && m < 5; m++) {
                      const item = val[m];
                      if (typeof item === "object" && item !== null) {
                        const itemKeys = Object.getOwnPropertyNames(item);
                        r += `        [${m}]: object with props: ${itemKeys.join(", ")}\n`;
                        for (let n = 0; n < itemKeys.length; n++) {
                          try {
                            const iv = item[itemKeys[n]];
                            if (typeof iv === "string" || typeof iv === "number" || typeof iv === "boolean" || iv === null) {
                              r += `          ${itemKeys[n]}: ${JSON.stringify(iv)}\n`;
                            } else {
                              r += `          ${itemKeys[n]}: ${typeof iv}\n`;
                            }
                          } catch(e2) {
                            r += `          ${itemKeys[n]}: error\n`;
                          }
                        }
                      } else {
                        r += `        [${m}]: ${JSON.stringify(item)}\n`;
                      }
                    }
                  } else {
                    r += `      ${keys[k]}: ${valType}\n`;
                  }
                } catch(e2) {
                  r += `      ${keys[k]}: error reading\n`;
                }
              }
            } else {
              r += `    [${j}]: ${type} = ${String(rule)}\n`;
            }
          } catch(e) {
            r += `    [${j}]: error — ${e.message}\n`;
          }
        }
      } else {
        r += `  archivedFilterRules: ${typeof rules} = ${String(rules)}\n`;
      }
    } catch(e) {
      r += `  archivedFilterRules: error — ${e.message}\n`;
    }

    // archivedTopLevelFilterAggregation
    try {
      const agg = p.archivedTopLevelFilterAggregation;
      r += `  archivedTopLevelFilterAggregation: ${JSON.stringify(agg)}\n`;
    } catch(e) {
      r += `  archivedTopLevelFilterAggregation: error — ${e.message}\n`;
    }

    // iconColor
    try {
      const color = p.iconColor;
      if (color === undefined) {
        r += `  iconColor: undefined\n`;
      } else if (color === null) {
        r += `  iconColor: null\n`;
      } else {
        // Try to extract color info
        const colorProps = Object.getOwnPropertyNames(color);
        r += `  iconColor: object with props: ${colorProps.join(", ")}\n`;
        for (let k = 0; k < colorProps.length; k++) {
          try {
            const val = color[colorProps[k]];
            r += `    ${colorProps[k]}: ${JSON.stringify(val)}\n`;
          } catch(e2) {
            r += `    ${colorProps[k]}: error\n`;
          }
        }
      }
    } catch(e) {
      r += `  iconColor: error — ${e.message}\n`;
    }

    r += `\n`;
  }

  // =============================================
  // PART 2: Enum extra props
  // =============================================
  r += `\n=== PART 2: Enum Object Props ===\n\n`;

  const enums = [
    { label: "Task.Status", obj: Task.Status },
    { label: "Task.RepetitionScheduleType", obj: Task.RepetitionScheduleType },
    { label: "Task.AnchorDateKey", obj: Task.AnchorDateKey },
    { label: "Task.RepetitionMethod", obj: Task.RepetitionMethod },
    { label: "Task.TagInsertionLocation", obj: Task.TagInsertionLocation },
    { label: "Task.ChildInsertionLocation", obj: Task.ChildInsertionLocation },
    { label: "Task.Notification", obj: Task.Notification },
    { label: "Project.Status", obj: Project.Status },
    { label: "Project.ReviewInterval", obj: Project.ReviewInterval },
    { label: "Tag.Status", obj: Tag.Status },
    { label: "Tag.ChildInsertionLocation", obj: Tag.ChildInsertionLocation },
    { label: "Tag.TaskInsertionLocation", obj: Tag.TaskInsertionLocation },
    { label: "Folder.Status", obj: Folder.Status },
    { label: "Folder.ChildInsertionLocation", obj: Folder.ChildInsertionLocation },
  ];

  for (let i = 0; i < enums.length; i++) {
    const e = enums[i];
    r += `--- ${e.label} ---\n`;
    try {
      const props = Object.getOwnPropertyNames(e.obj);
      r += `  Total props: ${props.length}\n`;
      for (let j = 0; j < props.length; j++) {
        const name = props[j];
        try {
          const val = e.obj[name];
          const type = typeof val;
          if (type === "function") {
            r += `  ${name}: function\n`;
          } else if (val === undefined) {
            r += `  ${name}: undefined\n`;
          } else if (val === null) {
            r += `  ${name}: null\n`;
          } else if (Array.isArray(val)) {
            r += `  ${name}: Array(${val.length})\n`;
          } else if (type === "string" || type === "number" || type === "boolean") {
            r += `  ${name}: ${type} = ${JSON.stringify(val)}\n`;
          } else {
            // Opaque object — try toString
            r += `  ${name}: ${type} [${String(val)}]\n`;
          }
        } catch(e2) {
          r += `  ${name}: error — ${e2.message}\n`;
        }
      }
    } catch(e2) {
      r += `  Cannot enumerate: ${e2.message}\n`;
    }
    r += `\n`;
  }

  return r;
})();
