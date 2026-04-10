// Cleanup — Delete TZ-DD-* Test Tasks
// WRITES TO OMNIFOCUS DATABASE (deletes test data)
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Finds all tasks where name starts with "TZ-DD-" or "TZ-PROBE-" and deletes them.

(() => {
  let r = `=== Timezone Deep-Dive Cleanup ===\n\n`;

  // Find all TZ-DD-* tasks
  const allTasks = flattenedTasks;
  let toDelete = [];
  for (let i = 0; i < allTasks.length; i++) {
    if (allTasks[i].name.indexOf("TZ-DD-") === 0 || allTasks[i].name.indexOf("TZ-PROBE-") === 0) {
      toDelete.push(allTasks[i]);
    }
  }

  r += `Found ${toDelete.length} TZ-DD-*/TZ-PROBE-* tasks to delete.\n\n`;

  if (toDelete.length === 0) {
    return r + "Nothing to clean up.\n";
  }

  // Delete each
  r += `--- Deleting ---\n`;
  let deleted = 0;
  let errors = 0;
  for (const t of toDelete) {
    const name = t.name;
    const id = t.id.primaryKey;
    try {
      deleteObject(t);
      r += `  Deleted: "${name}" (${id})\n`;
      deleted++;
    } catch (e) {
      r += `  Error deleting "${name}": ${e.message}\n`;
      errors++;
    }
  }

  // Verification: re-scan
  r += `\n--- Verification ---\n`;
  let remaining = 0;
  const tasksAfter = flattenedTasks;
  for (let i = 0; i < tasksAfter.length; i++) {
    if (tasksAfter[i].name.indexOf("TZ-DD-") === 0 || tasksAfter[i].name.indexOf("TZ-PROBE-") === 0) {
      remaining++;
      r += `  Still present: "${tasksAfter[i].name}"\n`;
    }
  }

  r += `\nDeleted: ${deleted}\n`;
  r += `Errors:  ${errors}\n`;
  r += `Remaining TZ-DD-*/TZ-PROBE-* tasks: ${remaining}\n`;
  r += remaining === 0 ? "\nCleanup complete.\n" : "\nWARNING: Some tasks remain!\n";

  return r;
})();
