// 03 — Status Enum Discovery
// READ-ONLY — no modifications to OmniFocus data
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Discovers all possible enum values for all entity types.
// Tests cross-type compatibility (is Project.Status.Active === Tag.Status.Active?).
// Determines the complete set of constants we need to handle.

(() => {
  let r = `=== 03: Status Enum Discovery ===\n\n`;

  // --- Part 1: Collect actual values from database ---
  r += `--- Part 1: Actual Values from Database ---\n\n`;

  // Enum-to-string helpers (String() returns "[object Object]" in Omni Automation)
  function matchProjectStatus(val) {
    if (val === null || val === undefined) return "null";
    try { if (val === Project.Status.Active) return "Active"; } catch(e) {}
    try { if (val === Project.Status.Done) return "Done"; } catch(e) {}
    try { if (val === Project.Status.Dropped) return "Dropped"; } catch(e) {}
    try { if (val === Project.Status.OnHold) return "OnHold"; } catch(e) {}
    return "UNKNOWN";
  }

  function matchTaskStatus(val) {
    if (val === null || val === undefined) return "null";
    try { if (val === Task.Status.Available) return "Available"; } catch(e) {}
    try { if (val === Task.Status.Blocked) return "Blocked"; } catch(e) {}
    try { if (val === Task.Status.Completed) return "Completed"; } catch(e) {}
    try { if (val === Task.Status.Dropped) return "Dropped"; } catch(e) {}
    try { if (val === Task.Status.DueSoon) return "DueSoon"; } catch(e) {}
    try { if (val === Task.Status.Next) return "Next"; } catch(e) {}
    try { if (val === Task.Status.Overdue) return "Overdue"; } catch(e) {}
    return "UNKNOWN";
  }

  function matchTagStatus(val) {
    if (val === null || val === undefined) return "null";
    try { if (val === Tag.Status.Active) return "Active"; } catch(e) {}
    try { if (val === Tag.Status.OnHold) return "OnHold"; } catch(e) {}
    try { if (val === Tag.Status.Dropped) return "Dropped"; } catch(e) {}
    return "UNKNOWN";
  }

  function matchFolderStatus(val) {
    if (val === null || val === undefined) return "null";
    try { if (val === Folder.Status.Active) return "Active"; } catch(e) {}
    try { if (val === Folder.Status.Dropped) return "Dropped"; } catch(e) {}
    return "UNKNOWN";
  }

  // Project statuses
  const projects = flattenedProjects;
  let projStatuses = {};
  for (let i = 0; i < projects.length; i++) {
    const s = projects[i].status;
    const key = (s === null || s === undefined) ? "null" : `[object: ${typeof s}]`;
    projStatuses[key] = (projStatuses[key] || 0) + 1;
  }
  r += `Project.status types: ${JSON.stringify(projStatuses)}\n`;

  // Task statuses (all tasks)
  const tasks = flattenedTasks;
  let taskStatuses = {};
  const taskSample = tasks.length;
  for (let i = 0; i < taskSample; i++) {
    const s = tasks[i].taskStatus;
    const key = (s === null || s === undefined) ? "null" : `[object: ${typeof s}]`;
    taskStatuses[key] = (taskStatuses[key] || 0) + 1;
  }
  r += `Task.taskStatus types (first ${taskSample}): ${JSON.stringify(taskStatuses)}\n`;

  // Tag statuses
  const tags = flattenedTags;
  let tagStatuses = {};
  for (let i = 0; i < tags.length; i++) {
    const s = tags[i].status;
    const key = (s === null || s === undefined) ? "null" : `[object: ${typeof s}]`;
    tagStatuses[key] = (tagStatuses[key] || 0) + 1;
  }
  r += `Tag.status types: ${JSON.stringify(tagStatuses)}\n`;

  // Folder statuses
  const folders = flattenedFolders;
  let folderStatuses = {};
  for (let i = 0; i < folders.length; i++) {
    const s = folders[i].status;
    const key = (s === null || s === undefined) ? "null" : `[object: ${typeof s}]`;
    folderStatuses[key] = (folderStatuses[key] || 0) + 1;
  }
  r += `Folder.status types: ${JSON.stringify(folderStatuses)}\n\n`;

  // --- Part 2: Test known constants by === comparison ---
  r += `--- Part 2: Known Constants (=== matching) ---\n\n`;

  // Project status distribution via === matching
  let projStatusDist = {};
  for (let i = 0; i < projects.length; i++) {
    const label = matchProjectStatus(projects[i].status);
    projStatusDist[label] = (projStatusDist[label] || 0) + 1;
  }
  r += `Project.Status distribution (=== match):\n`;
  for (const [k, v] of Object.entries(projStatusDist)) r += `  ${k}: ${v}\n`;

  // Task status distribution via === matching (sample)
  let taskStatusDist = {};
  for (let i = 0; i < taskSample; i++) {
    const label = matchTaskStatus(tasks[i].taskStatus);
    taskStatusDist[label] = (taskStatusDist[label] || 0) + 1;
  }
  r += `\nTask.Status distribution (=== match, first ${taskSample}):\n`;
  for (const [k, v] of Object.entries(taskStatusDist)) r += `  ${k}: ${v}\n`;

  // --- Part 3: Test Tag.Status and Folder.Status constants ---
  r += `\n--- Part 3: Tag.Status and Folder.Status Constants ---\n\n`;

  // Test if Tag.Status exists and what constants it has
  r += `Tag.Status exists: `;
  try {
    const ts = Tag.Status;
    r += `YES\n`;
    const tagConstants = ["Active", "OnHold", "Dropped"];
    for (const c of tagConstants) {
      try {
        const val = Tag.Status[c];
        r += `  Tag.Status.${c}: ${val !== undefined ? "EXISTS" : "undefined"}\n`;
      } catch(e) {
        r += `  Tag.Status.${c}: ERROR (${e.message})\n`;
      }
    }
  } catch(e) {
    r += `NO (${e.message})\n`;
  }

  // Tag status via === matching
  let tagStatusDist = {};
  for (let i = 0; i < tags.length; i++) {
    const label = matchTagStatus(tags[i].status);
    tagStatusDist[label] = (tagStatusDist[label] || 0) + 1;
  }
  r += `\nTag.Status distribution (=== match):\n`;
  for (const [k, v] of Object.entries(tagStatusDist)) r += `  ${k}: ${v}\n`;

  // Folder.Status
  r += `\nFolder.Status exists: `;
  try {
    const fs = Folder.Status;
    r += `YES\n`;
    const folderConstants = ["Active", "Dropped"];
    for (const c of folderConstants) {
      try {
        const val = Folder.Status[c];
        r += `  Folder.Status.${c}: ${val !== undefined ? "EXISTS" : "undefined"}\n`;
      } catch(e) {
        r += `  Folder.Status.${c}: ERROR (${e.message})\n`;
      }
    }
  } catch(e) {
    r += `NO (${e.message})\n`;
  }

  let folderStatusDist = {};
  for (let i = 0; i < folders.length; i++) {
    const label = matchFolderStatus(folders[i].status);
    folderStatusDist[label] = (folderStatusDist[label] || 0) + 1;
  }
  r += `\nFolder.Status distribution (=== match):\n`;
  for (const [k, v] of Object.entries(folderStatusDist)) r += `  ${k}: ${v}\n`;

  // --- Part 4: Cross-type compatibility ---
  r += `\n--- Part 4: Cross-Type Compatibility ---\n\n`;

  try {
    r += `Project.Status.Active === Tag.Status.Active: ${Project.Status.Active === Tag.Status.Active}\n`;
  } catch(e) {
    r += `Project.Status.Active === Tag.Status.Active: ERROR (${e.message})\n`;
  }

  try {
    r += `Project.Status.Dropped === Tag.Status.Dropped: ${Project.Status.Dropped === Tag.Status.Dropped}\n`;
  } catch(e) {
    r += `Project.Status.Dropped === Tag.Status.Dropped: ERROR (${e.message})\n`;
  }

  try {
    r += `Project.Status.Active === Folder.Status.Active: ${Project.Status.Active === Folder.Status.Active}\n`;
  } catch(e) {
    r += `Project.Status.Active === Folder.Status.Active: ERROR (${e.message})\n`;
  }

  try {
    r += `Tag.Status.Active === Folder.Status.Active: ${Tag.Status.Active === Folder.Status.Active}\n`;
  } catch(e) {
    r += `Tag.Status.Active === Folder.Status.Active: ERROR (${e.message})\n`;
  }

  // Test if OnHold exists on Project.Status
  r += `\nProject.Status.OnHold exists: `;
  try {
    const val = Project.Status.OnHold;
    r += `${val !== undefined ? "YES" : "NO (undefined)"}\n`;
  } catch(e) {
    r += `ERROR (${e.message})\n`;
  }

  // Test if there are additional unknown constants
  r += `\n--- Part 5: Exhaustive Constant Probe ---\n`;
  const candidates = ["Active", "OnHold", "Done", "Dropped", "Blocked", "Available",
                       "Completed", "DueSoon", "Next", "Overdue", "Inactive", "Paused",
                       "Archived", "Pending", "Deferred"];

  // Explicit type lookup map (no eval)
  const typeMap = { Project: Project, Task: Task, Tag: Tag, Folder: Folder };
  for (const typeName of ["Project", "Task", "Tag", "Folder"]) {
    let found = [];
    const typeObj = typeMap[typeName];
    for (const c of candidates) {
      try {
        if (typeObj.Status && typeObj.Status[c] !== undefined) {
          found.push(c);
        }
      } catch(e) {}
    }
    r += `${typeName}.Status constants found: ${found.length > 0 ? found.join(", ") : "NONE"}\n`;
  }

  return r;
})();
