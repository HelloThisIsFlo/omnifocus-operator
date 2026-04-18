// v1.4.1 Cache Coverage — OmniJS per-row cross-check (optional)
//
// Run in OmniFocus's Automation > Show Console. Output goes to the console;
// copy-paste it back to Claude so the diff section in FINDINGS.md can be
// completed.
//
// What this does:
//   For 20 sampled tasks (10 with no children, 10 with children), dump
//   { id, completedByChildren, sequential, hasAttachments } — the OmniJS
//   truth for these fields. Claude already has the SQLite values; the diff
//   confirms per-row identity between cache and bridge.
//
// Read-only: no writes, no state changes.

(() => {
  const results = [];
  const allTasks = flattenedTasks;

  // Sample strategy: pick tasks with varying shapes to exercise both rare and
  // common cases (e.g., the 0.9% that are sequential=true, the 0.2% with
  // attachments). We grab the first N of each to keep output stable.
  const withChildren = allTasks.filter(t => t.tasks.length > 0).slice(0, 10);
  const leaves = allTasks.filter(t => t.tasks.length === 0).slice(0, 10);

  for (const t of [...withChildren, ...leaves]) {
    results.push({
      id: t.id.primaryKey,
      name: (t.name || "").slice(0, 60),
      hasChildren: t.tasks.length > 0,
      completedByChildren: t.completedByChildren,
      sequential: t.sequential,
      hasAttachments: t.attachments.length > 0,
      attachmentCount: t.attachments.length,
    });
  }

  console.log("=== v1.4.1 cache-coverage OmniJS cross-check ===");
  console.log(JSON.stringify(results, null, 2));
  console.log("=== end ===");
})();
