// 25 — Method Enumeration
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Systematically enumerates ALL properties and methods on every entity type
// using JavaScript reflection. For each type, probes:
// - Instance properties and methods (via prototype chain)
// - Own properties on a sample instance
// - Static properties/methods on the class constructor
//
// Entity types probed: Task, Project, Tag, Folder, Perspective,
// Task.RepetitionRule, plus Document and Application

(() => {
  let r = `=== 25: Method Enumeration ===\n\n`;

  // Helper: collect all property names up the prototype chain
  function getAllPropertyNames(obj) {
    const props = new Set();
    let current = obj;
    while (current && current !== Object.prototype) {
      try {
        const names = Object.getOwnPropertyNames(current);
        for (let i = 0; i < names.length; i++) {
          props.add(names[i]);
        }
      } catch(e) {
        // Some prototypes may not be enumerable
      }
      try {
        current = Object.getPrototypeOf(current);
      } catch(e) {
        break;
      }
    }
    return Array.from(props).sort();
  }

  // Helper: classify a property on an object
  function classifyProp(obj, name) {
    try {
      const desc = Object.getOwnPropertyDescriptor(obj, name);
      if (desc) {
        if (typeof desc.value === "function") return "method";
        if (desc.get) return "getter";
        if (desc.set && !desc.get) return "setter";
        return "value:" + typeof desc.value;
      }
      // Not own — try accessing directly
      const val = obj[name];
      if (typeof val === "function") return "method";
      return "prop:" + typeof val;
    } catch(e) {
      return "error:" + e.message;
    }
  }

  // Probe a single entity
  function probeEntity(label, obj) {
    r += `\n=== ${label} ===\n`;
    if (!obj) {
      r += `  [no sample available]\n`;
      return;
    }

    // Enumerate from prototype chain
    const allProps = getAllPropertyNames(obj);
    r += `Total properties found: ${allProps.length}\n`;

    const methods = [];
    const getters = [];
    const values = [];
    const errors = [];

    for (let i = 0; i < allProps.length; i++) {
      const name = allProps[i];
      if (name === "constructor") continue;

      const classification = classifyProp(obj, name);
      if (!classification) continue;

      if (classification === "method") {
        methods.push({ name: name });
      } else if (classification === "getter") {
        try {
          const val = obj[name];
          const type = val === null ? "null" :
                       val === undefined ? "undefined" :
                       val instanceof Date ? "Date" :
                       Array.isArray(val) ? "Array(" + val.length + ")" :
                       typeof val;
          getters.push({ name: name, type: type });
        } catch(e) {
          getters.push({ name: name, type: "error: " + e.message });
        }
      } else if (classification.indexOf("error") === 0) {
        errors.push({ name: name, info: classification });
      } else {
        try {
          const val = obj[name];
          const type = val === null ? "null" :
                       val === undefined ? "undefined" :
                       val instanceof Date ? "Date" :
                       Array.isArray(val) ? "Array(" + val.length + ")" :
                       typeof val;
          values.push({ name: name, type: type });
        } catch(e) {
          values.push({ name: name, type: "error: " + e.message });
        }
      }
    }

    // Report methods
    r += `\n  --- Methods (${methods.length}) ---\n`;
    for (let i = 0; i < methods.length; i++) {
      r += `    ${methods[i].name}()\n`;
    }

    // Report getters
    r += `\n  --- Getters (${getters.length}) ---\n`;
    for (let i = 0; i < getters.length; i++) {
      r += `    ${getters[i].name}: ${getters[i].type}\n`;
    }

    // Report value properties
    r += `\n  --- Value Properties (${values.length}) ---\n`;
    for (let i = 0; i < values.length; i++) {
      r += `    ${values[i].name}: ${values[i].type}\n`;
    }

    // Report errors
    if (errors.length > 0) {
      r += `\n  --- Errors (${errors.length}) ---\n`;
      for (let i = 0; i < errors.length; i++) {
        r += `    ${errors[i].name}: ${errors[i].info}\n`;
      }
    }
  }

  // Probe static/class-level properties
  function probeClass(label, cls) {
    r += `\n=== ${label} (static) ===\n`;
    if (!cls) {
      r += `  [class not available]\n`;
      return;
    }

    let names;
    try {
      names = Object.getOwnPropertyNames(cls);
    } catch(e) {
      r += `  [cannot enumerate: ${e.message}]\n`;
      return;
    }

    const statics = [];
    for (let i = 0; i < names.length; i++) {
      const name = names[i];
      if (name === "prototype" || name === "length" || name === "name") continue;
      try {
        const val = cls[name];
        const type = typeof val;
        if (type === "function") {
          statics.push({ name: name, kind: "static method" });
        } else if (type === "object" && val !== null) {
          // Could be an enum namespace (like Task.Status)
          let subKeys;
          try {
            subKeys = Object.getOwnPropertyNames(val);
          } catch(e2) {
            subKeys = [];
          }
          statics.push({ name: name, kind: "object (" + subKeys.length + " props)" });
        } else {
          statics.push({ name: name, kind: type + "=" + String(val) });
        }
      } catch(e) {
        statics.push({ name: name, kind: "error: " + e.message });
      }
    }

    r += `  Static members: ${statics.length}\n`;
    for (let i = 0; i < statics.length; i++) {
      r += `    ${statics[i].name}: ${statics[i].kind}\n`;
    }
  }

  // --- Get sample entities ---
  const sampleTask = flattenedTasks[0];
  const sampleProject = flattenedProjects[0];
  const sampleTag = flattenedTags[0];
  const sampleFolder = flattenedFolders[0];
  const samplePerspective = Perspective.all[0];

  // Find a task with a repetitionRule
  let sampleRule = null;
  for (let i = 0; i < flattenedTasks.length; i++) {
    if (flattenedTasks[i].repetitionRule) {
      sampleRule = flattenedTasks[i].repetitionRule;
      break;
    }
  }

  // --- Probe instances ---
  probeEntity("Task (instance)", sampleTask);
  probeEntity("Project (instance)", sampleProject);
  probeEntity("Tag (instance)", sampleTag);
  probeEntity("Folder (instance)", sampleFolder);
  probeEntity("Perspective (instance)", samplePerspective);
  probeEntity("RepetitionRule (instance)", sampleRule);
  probeEntity("Document", document);
  probeEntity("Application", app);

  // --- Probe class statics ---
  probeClass("Task", Task);
  probeClass("Project", Project);
  probeClass("Tag", Tag);
  probeClass("Folder", Folder);
  probeClass("Perspective", Perspective);

  return r;
})();
