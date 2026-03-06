// 16 — Sequential Project Deep Dive
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Examines sequential projects to verify task ordering patterns
// and check for the "Overdue masks Blocked" scenario: tasks with past
// due dates that are sequentially blocked but show Overdue status.

(() => {
  let r = `=== 16: Sequential Project Deep Dive ===\n\n`;

  function resolveTaskStatus(t) {
    const s = t.taskStatus;
    if (s === Task.Status.Available) return "Available";
    if (s === Task.Status.Blocked) return "Blocked";
    if (s === Task.Status.Completed) return "Completed";
    if (s === Task.Status.Dropped) return "Dropped";
    if (s === Task.Status.DueSoon) return "DueSoon";
    if (s === Task.Status.Next) return "Next";
    if (s === Task.Status.Overdue) return "Overdue";
    return "UNKNOWN";
  }

  function resolveProjStatus(p) {
    if (p.status === Project.Status.Active) return "Active";
    if (p.status === Project.Status.OnHold) return "OnHold";
    if (p.status === Project.Status.Done) return "Done";
    if (p.status === Project.Status.Dropped) return "Dropped";
    return "UNKNOWN";
  }

  // --- Find sequential vs parallel projects ---
  const allProjects = flattenedProjects;
  const seqProjects = [];
  const parProjects = [];
  for (let i = 0; i < allProjects.length; i++) {
    if (allProjects[i].sequential) {
      seqProjects.push(allProjects[i]);
    } else {
      parProjects.push(allProjects[i]);
    }
  }

  r += `Sequential projects: ${seqProjects.length}\n`;
  r += `Parallel projects: ${parProjects.length}\n\n`;

  // --- Show first 20 sequential projects with task details ---
  r += `--- Sequential Projects (first 20) ---\n`;
  const showCount = Math.min(seqProjects.length, 20);

  for (let i = 0; i < showCount; i++) {
    const p = seqProjects[i];
    r += `\nProject: "${p.name}" (${resolveProjStatus(p)})\n`;

    const children = p.task.children;
    r += `  Direct children: ${children.length}\n`;

    let firstIncompleteFound = false;
    for (let j = 0; j < children.length; j++) {
      const child = children[j];
      const status = resolveTaskStatus(child);
      const isComplete = child.completed;
      const isDropped = child.taskStatus === Task.Status.Dropped;

      let marker = "";
      if (!isComplete && !isDropped && !firstIncompleteFound) {
        firstIncompleteFound = true;
        marker = " <-- FIRST INCOMPLETE";
      }

      r += `    [${j}] "${child.name}" | ${status}`;
      r += ` | completed=${isComplete}`;
      if (child.dueDate) r += ` | due=${child.dueDate.toISOString().slice(0,10)}`;
      if (child.deferDate) r += ` | defer=${child.deferDate.toISOString().slice(0,10)}`;
      if (child.sequential) r += ` | sequential=true`;
      if (child.hasChildren) r += ` | hasChildren=true`;
      r += `${marker}\n`;
    }
  }

  // --- Check ALL sequential projects for Overdue-masks-Blocked ---
  r += `\n--- Overdue Tasks in ALL Sequential Projects ---\n`;
  let totalOverdueInSeq = 0;
  const overdueDetails = [];

  for (let i = 0; i < seqProjects.length; i++) {
    const p = seqProjects[i];
    const children = p.task.children;
    let firstIncompleteIdx = -1;

    for (let j = 0; j < children.length; j++) {
      const child = children[j];
      if (!child.completed && child.taskStatus !== Task.Status.Dropped) {
        if (firstIncompleteIdx === -1) firstIncompleteIdx = j;
      }
      if (child.taskStatus === Task.Status.Overdue) {
        totalOverdueInSeq++;
        overdueDetails.push({
          task: child.name,
          project: p.name,
          index: j,
          isFirstIncomplete: (firstIncompleteIdx === j),
          dueDate: child.dueDate ? child.dueDate.toISOString().slice(0,10) : "null",
          deferDate: child.deferDate ? child.deferDate.toISOString().slice(0,10) : "null"
        });
      }
    }
  }

  r += `Total Overdue tasks in sequential projects: ${totalOverdueInSeq}\n`;
  if (overdueDetails.length > 0) {
    for (let i = 0; i < overdueDetails.length; i++) {
      const d = overdueDetails[i];
      r += `  "${d.task}" in "${d.project}" [index ${d.index}]`;
      r += ` | due=${d.dueDate} | defer=${d.deferDate}`;
      if (d.isFirstIncomplete) {
        r += ` — IS first incomplete (genuinely overdue) ✅\n`;
      } else {
        r += ` — NOT first incomplete (Overdue masks Blocked!) ⚠️\n`;
      }
    }
  } else {
    r += `  None found.\n`;
  }

  // --- Sequential action groups (non-project tasks with sequential=true) ---
  r += `\n--- Sequential Action Groups ---\n`;
  const allTasks = flattenedTasks;
  let seqActionGroups = 0;
  for (let i = 0; i < allTasks.length; i++) {
    const t = allTasks[i];
    if (t.sequential && t.hasChildren) {
      seqActionGroups++;
    }
  }
  r += `Tasks with sequential=true AND hasChildren=true: ${seqActionGroups}\n`;
  r += `(These are action groups that behave like mini-sequential projects)\n`;

  // --- Summary ---
  r += `\n--- Summary ---\n`;
  r += `Sequential projects: ${seqProjects.length}\n`;
  r += `Overdue tasks in sequential projects: ${totalOverdueInSeq}\n`;
  if (totalOverdueInSeq > 0) {
    let maskedCount = 0;
    for (let i = 0; i < overdueDetails.length; i++) {
      if (!overdueDetails[i].isFirstIncomplete) maskedCount++;
    }
    r += `Overdue-masks-Blocked instances: ${maskedCount}\n`;
  }
  r += `Sequential action groups: ${seqActionGroups}\n`;

  return r;
})();
