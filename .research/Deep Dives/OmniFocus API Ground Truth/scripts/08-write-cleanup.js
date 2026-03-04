// 08 — [WRITE] Cleanup
// ⚠️ WRITES TO OMNIFOCUS DATABASE (deletes test data)
//
// Finds all entities tagged "🧪 API Audit" and deletes them.
// Deletes: tasks first, then project, then tag.
// Verifies: nothing tagged "🧪 API Audit" remains.

(() => {
  const app = Application("OmniFocus");
  const doc = app.defaultDocument;

  let r = `=== 08: [WRITE] Cleanup ===\n\n`;

  // Find the audit tag
  const allTags = doc.flattenedTags();
  let auditTag = null;
  for (let i = 0; i < allTags.length; i++) {
    if (allTags[i].name() === "🧪 API Audit") {
      auditTag = allTags[i];
      break;
    }
  }

  if (!auditTag) {
    return r + `Tag "🧪 API Audit" not found — nothing to clean up. ✅\n`;
  }
  r += `Found tag: "${auditTag.name()}" (id: ${auditTag.id()})\n\n`;

  // Find all tasks with this tag
  const allTasks = doc.flattenedTasks();
  let tasksToDelete = [];
  for (let i = 0; i < allTasks.length; i++) {
    const taskTags = allTasks[i].tags();
    for (let j = 0; j < taskTags.length; j++) {
      if (taskTags[j].id() === auditTag.id()) {
        tasksToDelete.push(allTasks[i]);
        break;
      }
    }
  }
  r += `Found ${tasksToDelete.length} tasks with audit tag.\n`;

  // Find test project
  const allProjects = doc.flattenedProjects();
  let testProject = null;
  for (let i = 0; i < allProjects.length; i++) {
    if (allProjects[i].name() === "🧪 API Audit Test Project") {
      testProject = allProjects[i];
      break;
    }
  }

  // Delete tasks first (children before parents)
  // Sort by depth (deepest first) — approximate by checking if parent is in our list
  for (let i = 0; i < tasksToDelete.length; i++) {
    const t = tasksToDelete[i];
    try {
      r += `  Deleting task: "${t.name()}" (id: ${t.id()})...\n`;
      app.delete(t);
      r += `    ✅ Deleted\n`;
    } catch(e) {
      r += `    ⚠️ Error: ${e.message}\n`;
    }
  }

  // Delete project
  if (testProject) {
    r += `\nDeleting project: "${testProject.name()}" (id: ${testProject.id()})...\n`;
    try {
      app.delete(testProject);
      r += `  ✅ Deleted\n`;
    } catch(e) {
      r += `  ⚠️ Error: ${e.message}\n`;
    }
  } else {
    r += `\nProject "🧪 API Audit Test Project" not found — may have been deleted with tasks.\n`;
  }

  // Delete tag
  r += `\nDeleting tag: "${auditTag.name()}" (id: ${auditTag.id()})...\n`;
  try {
    app.delete(auditTag);
    r += `  ✅ Deleted\n`;
  } catch(e) {
    r += `  ⚠️ Error: ${e.message}\n`;
  }

  // --- Verification ---
  r += `\n--- Verification ---\n`;

  // Check tag is gone
  const tagsAfter = doc.flattenedTags();
  let tagFound = false;
  for (let i = 0; i < tagsAfter.length; i++) {
    if (tagsAfter[i].name() === "🧪 API Audit") {
      tagFound = true;
      break;
    }
  }
  r += `Tag "🧪 API Audit" still exists: ${tagFound ? "YES ⚠️" : "NO ✅"}\n`;

  // Check project is gone
  const projectsAfter = doc.flattenedProjects();
  let projFound = false;
  for (let i = 0; i < projectsAfter.length; i++) {
    if (projectsAfter[i].name() === "🧪 API Audit Test Project") {
      projFound = true;
      break;
    }
  }
  r += `Project "🧪 API Audit Test Project" still exists: ${projFound ? "YES ⚠️" : "NO ✅"}\n`;

  r += `\nCleanup complete.\n`;

  return r;
})();
