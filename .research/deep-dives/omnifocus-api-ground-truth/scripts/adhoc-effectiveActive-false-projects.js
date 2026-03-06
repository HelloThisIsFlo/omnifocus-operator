// Ad-hoc: List all projects where effectiveActive=false on root task
// Shows project name, project status, active, effectiveActive, and folder path
(() => {
  const projects = flattenedProjects;
  const results = [];

  for (const p of projects) {
    const t = p.task;
    if (t.effectiveActive === false) {
      // Build folder path
      const folders = [];
      let f = p.folder;
      while (f) {
        folders.unshift(f.name);
        f = f.parent;
      }
      const folderPath = folders.join(" > ") || "(top-level)";

      // Resolve project status
      let statusStr = "UNKNOWN";
      if (p.status === Project.Status.Active) statusStr = "Active";
      else if (p.status === Project.Status.OnHold) statusStr = "OnHold";
      else if (p.status === Project.Status.Done) statusStr = "Done";
      else if (p.status === Project.Status.Dropped) statusStr = "Dropped";

      results.push({
        name: p.name,
        status: statusStr,
        active: t.active,
        effectiveActive: t.effectiveActive,
        folderPath: folderPath
      });
    }
  }

  // Sort by folder path then name
  results.sort((a, b) => a.folderPath.localeCompare(b.folderPath) || a.name.localeCompare(b.name));

  console.log(`=== Projects with effectiveActive=false (${results.length}/${projects.length}) ===\n`);

  // Group by folder path
  let currentFolder = null;
  for (const r of results) {
    if (r.folderPath !== currentFolder) {
      currentFolder = r.folderPath;
      console.log(`\n--- ${currentFolder} ---`);
    }
    console.log(`  ${r.status.padEnd(8)} | active=${String(r.active).padEnd(5)} | ${r.name}`);
  }

  // Summary by status
  const byStat = {};
  for (const r of results) {
    byStat[r.status] = (byStat[r.status] || 0) + 1;
  }
  console.log(`\n--- Summary ---`);
  for (const [s, c] of Object.entries(byStat)) {
    console.log(`  ${s}: ${c}`);
  }

  // Unique folders involved
  const uniqueFolders = [...new Set(results.map(r => r.folderPath))];
  console.log(`\nFolders involved: ${uniqueFolders.length}`);
  for (const f of uniqueFolders) {
    console.log(`  ${f}`);
  }
})();
