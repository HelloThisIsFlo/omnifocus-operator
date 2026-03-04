// 05 — [WRITE] Create Test Data
// ⚠️ WRITES TO OMNIFOCUS DATABASE
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Creates controlled test data for write-side verification:
// - A tag: "🧪 API Audit"
// - A project: "🧪 API Audit Test Project" (tagged, with due date and note)
// - Task 1 under project: "🧪 Test Task 1" (tagged, with due date)
// - Task 2 under project: "🧪 Test Task 2" (tagged, flagged, deferred)
//
// All test entities use the "🧪 API Audit" tag for identification and cleanup.

(() => {
  let r = `=== 05: [WRITE] Create Test Data ===\n\n`;

  // --- Create tag ---
  r += `Creating tag "🧪 API Audit"...\n`;
  const tag = new Tag("🧪 API Audit");
  r += `  Tag created: id=${tag.id.primaryKey}, name="${tag.name}"\n`;

  // --- Create project ---
  r += `\nCreating project "🧪 API Audit Test Project"...\n`;
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(17, 0, 0, 0);

  const project = new Project("🧪 API Audit Test Project");
  project.note = "Test project for OmniFocus API Ground Truth audit. Safe to delete.";
  project.dueDate = tomorrow;

  // Add tag to project
  project.addTag(tag);
  r += `  Project created: id=${project.id.primaryKey}, name="${project.name}"\n`;
  r += `  Project dueDate: ${project.dueDate}\n`;
  r += `  Project note: "${project.note}"\n`;
  r += `  Project tags: ${project.tags.map(t => t.name).join(", ")}\n`;

  // --- Create task 1 ---
  r += `\nCreating task "🧪 Test Task 1"...\n`;
  const nextWeek = new Date();
  nextWeek.setDate(nextWeek.getDate() + 7);
  nextWeek.setHours(17, 0, 0, 0);

  const task1 = new Task("🧪 Test Task 1", project);
  task1.note = "First test task for API audit.";
  task1.dueDate = nextWeek;
  task1.addTag(tag);
  r += `  Task 1 created: id=${task1.id.primaryKey}, name="${task1.name}"\n`;
  r += `  Task 1 dueDate: ${task1.dueDate}\n`;
  r += `  Task 1 tags: ${task1.tags.map(t => t.name).join(", ")}\n`;

  // --- Create task 2 ---
  r += `\nCreating task "🧪 Test Task 2"...\n`;
  const deferDate = new Date();
  deferDate.setDate(deferDate.getDate() + 3);
  deferDate.setHours(9, 0, 0, 0);

  const task2 = new Task("🧪 Test Task 2", project);
  task2.note = "Second test task — flagged and deferred.";
  task2.flagged = true;
  task2.deferDate = deferDate;
  task2.addTag(tag);
  r += `  Task 2 created: id=${task2.id.primaryKey}, name="${task2.name}"\n`;
  r += `  Task 2 flagged: ${task2.flagged}\n`;
  r += `  Task 2 deferDate: ${task2.deferDate}\n`;
  r += `  Task 2 tags: ${task2.tags.map(t => t.name).join(", ")}\n`;

  // --- Summary ---
  r += `\n--- Summary ---\n`;
  r += `Created:\n`;
  r += `  1 tag:     "🧪 API Audit" (id: ${tag.id.primaryKey})\n`;
  r += `  1 project: "🧪 API Audit Test Project" (id: ${project.id.primaryKey})\n`;
  r += `  2 tasks:   "🧪 Test Task 1" (id: ${task1.id.primaryKey}), "🧪 Test Task 2" (id: ${task2.id.primaryKey})\n`;
  r += `\nAll entities tagged with "🧪 API Audit" for easy cleanup (Script 08).\n`;

  return r;
})();
