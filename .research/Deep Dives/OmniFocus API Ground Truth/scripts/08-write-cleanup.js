// 08 — [WRITE] Cleanup
// WRITES TO OMNIFOCUS DATABASE (deletes test data)
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Finds all entities tagged "API Audit" and deletes them.
// Strategy: delete projects first (cascades to their tasks), then orphan tasks, then the tag.

(() => {
  let r = `=== 08: [WRITE] Cleanup ===\n\n`;

  // Find the audit tag
  const TAG_NAME = "API Audit";
  const allTags = flattenedTags;
  let auditTag = null;
  for (let i = 0; i < allTags.length; i++) {
    if (allTags[i].name === TAG_NAME) {
      auditTag = allTags[i];
      break;
    }
  }

  if (!auditTag) {
    return r + `Tag "${TAG_NAME}" not found — nothing to clean up.\n`;
  }
  r += `Found tag: "${auditTag.name}" (id: ${auditTag.id.primaryKey})\n\n`;

  function hasAuditTag(entity) {
    const tags = entity.tags;
    for (let i = 0; i < tags.length; i++) {
      if (tags[i].id.primaryKey === auditTag.id.primaryKey) return true;
    }
    return false;
  }

  // Find all projects with this tag (check project-level tags)
  const allProjects = flattenedProjects;
  let projectsToDelete = [];
  for (let i = 0; i < allProjects.length; i++) {
    if (hasAuditTag(allProjects[i])) {
      projectsToDelete.push(allProjects[i]);
    }
  }
  r += `Found ${projectsToDelete.length} projects with audit tag.\n`;

  // Find all tasks with this tag
  const allTasks = flattenedTasks;
  let tasksWithTag = [];
  for (let i = 0; i < allTasks.length; i++) {
    if (hasAuditTag(allTasks[i])) {
      tasksWithTag.push(allTasks[i]);
    }
  }
  r += `Found ${tasksWithTag.length} tasks with audit tag.\n`;

  // Delete projects first (cascades to their tasks)
  r += `\n--- Deleting Projects ---\n`;
  for (const p of projectsToDelete) {
    const name = p.name;
    const id = p.id.primaryKey;
    try {
      deleteObject(p);
      r += `  Deleted project: "${name}" (${id})\n`;
    } catch(e) {
      r += `  Error deleting "${name}": ${e.message}\n`;
    }
  }

  // Delete any remaining orphan tasks (not owned by a deleted project)
  r += `\n--- Deleting Orphan Tasks ---\n`;
  let orphanCount = 0;
  for (const t of tasksWithTag) {
    try {
      const name = t.name;
      const id = t.id.primaryKey;
      deleteObject(t);
      r += `  Deleted task: "${name}" (${id})\n`;
      orphanCount++;
    } catch(e) {
      // Expected — task was already deleted with its project
    }
  }
  r += `  ${orphanCount} orphan tasks deleted (rest were deleted with projects).\n`;

  // Delete tag
  r += `\n--- Deleting Tag ---\n`;
  try {
    deleteObject(auditTag);
    r += `  Deleted tag: "${TAG_NAME}"\n`;
  } catch(e) {
    r += `  Error: ${e.message}\n`;
  }

  // --- Verification ---
  r += `\n--- Verification ---\n`;

  let tagStillExists = false;
  const tagsAfter = flattenedTags;
  for (let i = 0; i < tagsAfter.length; i++) {
    if (tagsAfter[i].name === TAG_NAME) {
      tagStillExists = true;
      break;
    }
  }
  r += `Tag "${TAG_NAME}" still exists: ${tagStillExists ? "YES" : "NO"}\n`;

  let auditProjectsRemain = 0;
  const projectsAfter = flattenedProjects;
  for (let i = 0; i < projectsAfter.length; i++) {
    if (projectsAfter[i].name.startsWith("Audit:")) auditProjectsRemain++;
  }
  r += `"Audit:" projects remaining: ${auditProjectsRemain}\n`;

  let auditTasksRemain = 0;
  // Re-check by scanning for any task whose name starts with common test prefixes
  const tasksAfter = flattenedTasks;
  for (let i = 0; i < tasksAfter.length; i++) {
    const tags = tasksAfter[i].tags;
    for (let j = 0; j < tags.length; j++) {
      if (tags[j].name === TAG_NAME) {
        auditTasksRemain++;
        break;
      }
    }
  }
  r += `Tasks with "${TAG_NAME}" tag remaining: ${auditTasksRemain}\n`;

  r += `\nCleanup complete.\n`;
  return r;
})();
