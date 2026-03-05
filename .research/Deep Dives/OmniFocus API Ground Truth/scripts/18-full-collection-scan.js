// 18 — Full Collection Scan + Object Structure Probe
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Scans ALL tasks for linkedFileURLs, notifications, and attachments.
// Reports counts, then probes the internal structure of Notification
// and Attachment objects (all properties, types, sample values).

(() => {
  let r = `=== 18: Full Collection Scan + Object Structure Probe ===\n\n`;

  const tasks = flattenedTasks;
  r += `Total tasks: ${tasks.length}\n\n`;

  let linkedCount = 0;
  let notifCount = 0;
  let attachCount = 0;
  const notifObjects = [];   // collect actual notification objects
  const attachObjects = [];  // collect actual attachment objects
  let errors = 0;

  for (let i = 0; i < tasks.length; i++) {
    const t = tasks[i];

    try {
      if (t.linkedFileURLs && t.linkedFileURLs.length > 0) {
        linkedCount++;
      }
    } catch(e) { errors++; }

    try {
      if (t.notifications && t.notifications.length > 0) {
        notifCount++;
        // Collect up to 10 notification objects for structure probing
        if (notifObjects.length < 10) {
          for (let j = 0; j < t.notifications.length && notifObjects.length < 10; j++) {
            notifObjects.push({ notif: t.notifications[j], taskName: t.name });
          }
        }
      }
    } catch(e) { errors++; }

    try {
      if (t.attachments && t.attachments.length > 0) {
        attachCount++;
        // Collect up to 10 attachment objects for structure probing
        if (attachObjects.length < 10) {
          for (let j = 0; j < t.attachments.length && attachObjects.length < 10; j++) {
            attachObjects.push({ attach: t.attachments[j], taskName: t.name });
          }
        }
      }
    } catch(e) { errors++; }
  }

  r += `--- Counts ---\n`;
  r += `linkedFileURLs non-empty: ${linkedCount}/${tasks.length}\n`;
  r += `notifications non-empty: ${notifCount}/${tasks.length}\n`;
  r += `attachments non-empty: ${attachCount}/${tasks.length}\n`;
  r += `Errors during scan: ${errors}\n`;

  // --- Probe Notification object structure ---
  r += `\n--- Notification Object Structure ---\n`;
  r += `Collected ${notifObjects.length} notification objects to probe\n\n`;

  if (notifObjects.length > 0) {
    // Enumerate all properties on first notification
    const firstNotif = notifObjects[0].notif;
    const notifProps = [];
    try {
      // Own properties
      const ownKeys = Object.getOwnPropertyNames(firstNotif);
      r += `Own properties: ${ownKeys.length > 0 ? ownKeys.join(", ") : "(none)"}\n`;
    } catch(e) {
      r += `Own properties: error — ${e.message}\n`;
    }

    // Probe known/likely property names
    const notifProbes = [
      "id", "kind", "type", "date", "absoluteFireDate", "relativeFireOffset",
      "nextFireDate", "fireDate", "isSnoozed", "task", "name", "identifier",
      "initialFireDate", "repeatInterval", "usesFloatingTimeZone",
      "soundName", "hasSound", "alertTitle", "alertBody",
      "triggerDate", "triggerDateOffset", "triggerType"
    ];

    r += `\nProperty probe on first Notification:\n`;
    for (let i = 0; i < notifProbes.length; i++) {
      const prop = notifProbes[i];
      try {
        const val = firstNotif[prop];
        if (val !== undefined) {
          let display;
          if (val === null) display = "null";
          else if (val instanceof Date) display = `Date(${val.toISOString()})`;
          else if (typeof val === "object") display = `[object] ${String(val)}`;
          else display = `${typeof val}: ${String(val)}`;
          r += `  .${prop} = ${display}\n`;
        }
      } catch(e) {
        r += `  .${prop} = ERROR: ${e.message}\n`;
      }
    }

    // Try prototype chain
    r += `\nPrototype probe:\n`;
    try {
      const proto = Object.getPrototypeOf(firstNotif);
      if (proto) {
        const protoNames = Object.getOwnPropertyNames(proto);
        r += `  Prototype properties: ${protoNames.join(", ")}\n`;

        // Probe each prototype property
        for (let i = 0; i < protoNames.length; i++) {
          const prop = protoNames[i];
          if (prop === "constructor") continue;
          try {
            const val = firstNotif[prop];
            let display;
            if (val === undefined) display = "undefined";
            else if (val === null) display = "null";
            else if (val instanceof Date) display = `Date(${val.toISOString()})`;
            else if (typeof val === "function") display = "function";
            else if (typeof val === "object") display = `[object] ${String(val)}`;
            else display = `${typeof val}: ${String(val)}`;
            r += `    .${prop} = ${display}\n`;
          } catch(e) {
            r += `    .${prop} = ERROR: ${e.message}\n`;
          }
        }
      } else {
        r += `  No prototype found\n`;
      }
    } catch(e) {
      r += `  Prototype error: ${e.message}\n`;
    }

    // Show sample values across multiple notifications
    r += `\n--- Notification Samples (${notifObjects.length}) ---\n`;
    for (let i = 0; i < notifObjects.length; i++) {
      const n = notifObjects[i].notif;
      let line = `  [${i}] `;
      // Try the most likely useful properties
      try { line += `kind=${String(n.kind)} `; } catch(e) { line += `kind=ERR `; }
      try {
        if (n.absoluteFireDate) line += `absFireDate=${n.absoluteFireDate.toISOString()} `;
        else line += `absFireDate=null `;
      } catch(e) { line += `absFireDate=ERR `; }
      try { line += `relFireOffset=${n.relativeFireOffset} `; } catch(e) { line += `relFireOffset=ERR `; }
      try { line += `isSnoozed=${n.isSnoozed} `; } catch(e) { line += `isSnoozed=ERR `; }
      try { line += `repeatInterval=${n.repeatInterval} `; } catch(e) { line += `repeatInterval=ERR `; }
      r += line + `\n`;
    }
  }

  // --- Probe Attachment object structure ---
  r += `\n--- Attachment Object Structure ---\n`;
  r += `Collected ${attachObjects.length} attachment objects to probe\n\n`;

  if (attachObjects.length > 0) {
    const firstAttach = attachObjects[0].attach;

    // Own properties
    try {
      const ownKeys = Object.getOwnPropertyNames(firstAttach);
      r += `Own properties: ${ownKeys.length > 0 ? ownKeys.join(", ") : "(none)"}\n`;
    } catch(e) {
      r += `Own properties: error — ${e.message}\n`;
    }

    // Probe known/likely property names
    const attachProbes = [
      "id", "name", "fileName", "fileURL", "url", "type", "mimeType",
      "contentType", "data", "size", "byteSize", "fileSize",
      "creationDate", "modificationDate", "identifier",
      "isImage", "image", "thumbnail", "fileType", "fileWrapper",
      "resourceURL", "localURL", "cloudURL"
    ];

    r += `\nProperty probe on first Attachment:\n`;
    for (let i = 0; i < attachProbes.length; i++) {
      const prop = attachProbes[i];
      try {
        const val = firstAttach[prop];
        if (val !== undefined) {
          let display;
          if (val === null) display = "null";
          else if (val instanceof Date) display = `Date(${val.toISOString()})`;
          else if (typeof val === "object") display = `[object] ${String(val)}`;
          else display = `${typeof val}: ${String(val)}`;
          r += `  .${prop} = ${display}\n`;
        }
      } catch(e) {
        r += `  .${prop} = ERROR: ${e.message}\n`;
      }
    }

    // Prototype chain
    r += `\nPrototype probe:\n`;
    try {
      const proto = Object.getPrototypeOf(firstAttach);
      if (proto) {
        const protoNames = Object.getOwnPropertyNames(proto);
        r += `  Prototype properties: ${protoNames.join(", ")}\n`;

        for (let i = 0; i < protoNames.length; i++) {
          const prop = protoNames[i];
          if (prop === "constructor") continue;
          try {
            const val = firstAttach[prop];
            let display;
            if (val === undefined) display = "undefined";
            else if (val === null) display = "null";
            else if (val instanceof Date) display = `Date(${val.toISOString()})`;
            else if (typeof val === "function") display = "function";
            else if (typeof val === "object") display = `[object] ${String(val)}`;
            else display = `${typeof val}: ${String(val)}`;
            r += `    .${prop} = ${display}\n`;
          } catch(e) {
            r += `    .${prop} = ERROR: ${e.message}\n`;
          }
        }
      } else {
        r += `  No prototype found\n`;
      }
    } catch(e) {
      r += `  Prototype error: ${e.message}\n`;
    }

    // Show sample values across multiple attachments
    r += `\n--- Attachment Samples (${attachObjects.length}) ---\n`;
    for (let i = 0; i < attachObjects.length; i++) {
      const a = attachObjects[i].attach;
      let line = `  [${i}] `;
      try { line += `name=${a.name} `; } catch(e) { line += `name=ERR `; }
      try { line += `type=${a.type} `; } catch(e) { line += `type=ERR `; }
      try { line += `size=${a.size || a.byteSize || a.fileSize} `; } catch(e) { line += `size=ERR `; }
      try { line += `fileURL=${a.fileURL || a.url} `; } catch(e) { line += `fileURL=ERR `; }
      r += line + `\n`;
    }
  }

  return r;
})();
