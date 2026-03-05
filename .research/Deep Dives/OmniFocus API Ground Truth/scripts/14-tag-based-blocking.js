// 14 — Tag-Based Blocking Investigation
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Checks whether tasks assigned to OnHold tags have different taskStatus
// distributions than other tasks. Critical for Milestone 2's recovery logic:
// if OnHold tags cause blocking, the service layer must account for it.

(() => {
  let r = `=== 14: Tag-Based Blocking Investigation ===\n\n`;

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

  // --- Find OnHold tags ---
  const allTags = flattenedTags;
  const onHoldTags = [];
  for (let i = 0; i < allTags.length; i++) {
    if (allTags[i].status === Tag.Status.OnHold) {
      onHoldTags.push(allTags[i]);
    }
  }
  r += `OnHold tags found: ${onHoldTags.length}\n`;
  for (let i = 0; i < onHoldTags.length; i++) {
    r += `  "${onHoldTags[i].name}" (id: ${onHoldTags[i].id.primaryKey})\n`;
  }

  if (onHoldTags.length === 0) {
    return r + `\nNo OnHold tags — cannot test tag-based blocking.\n`;
  }

  // Build set of OnHold tag IDs
  const onHoldIds = {};
  for (let i = 0; i < onHoldTags.length; i++) {
    onHoldIds[onHoldTags[i].id.primaryKey] = true;
  }

  // --- Scan all tasks ---
  const allTasks = flattenedTasks;
  const withOnHold = [];
  const withoutOnHold = [];

  for (let i = 0; i < allTasks.length; i++) {
    const t = allTasks[i];
    const tags = t.tags;
    let hasOnHoldTag = false;
    for (let j = 0; j < tags.length; j++) {
      if (onHoldIds[tags[j].id.primaryKey]) {
        hasOnHoldTag = true;
        break;
      }
    }
    if (hasOnHoldTag) {
      withOnHold.push(t);
    } else {
      withoutOnHold.push(t);
    }
  }

  r += `\nTasks with OnHold tag: ${withOnHold.length}\n`;
  r += `Tasks without OnHold tag: ${withoutOnHold.length}\n`;

  // --- Status distributions ---
  function statusDist(taskList) {
    const dist = {};
    for (let i = 0; i < taskList.length; i++) {
      const name = resolveTaskStatus(taskList[i]);
      dist[name] = (dist[name] || 0) + 1;
    }
    return dist;
  }

  const onHoldDist = statusDist(withOnHold);
  const normalDist = statusDist(withoutOnHold);

  r += `\n--- Status Distribution: Tasks WITH OnHold Tag ---\n`;
  const ohKeys = Object.keys(onHoldDist).sort();
  for (let i = 0; i < ohKeys.length; i++) {
    r += `  ${ohKeys[i]}: ${onHoldDist[ohKeys[i]]}\n`;
  }

  r += `\n--- Status Distribution: Tasks WITHOUT OnHold Tag ---\n`;
  const nKeys = Object.keys(normalDist).sort();
  for (let i = 0; i < nKeys.length; i++) {
    r += `  ${nKeys[i]}: ${normalDist[nKeys[i]]}\n`;
  }

  // --- Detailed look at OnHold-tagged tasks (first 50) ---
  r += `\n--- Detailed: Tasks with OnHold Tag (first 50) ---\n`;
  const showCount = Math.min(withOnHold.length, 50);
  for (let i = 0; i < showCount; i++) {
    const t = withOnHold[i];
    const statusName = resolveTaskStatus(t);
    const tagNames = [];
    const tags = t.tags;
    for (let j = 0; j < tags.length; j++) {
      tagNames.push(tags[j].name);
    }

    r += `  "${t.name}" | status=${statusName} | active=${t.active} | effActive=${t.effectiveActive}`;
    r += ` | tags=[${tagNames.join(", ")}]`;

    const cp = t.containingProject;
    if (cp) {
      let projStatus = "UNKNOWN";
      if (cp.status === Project.Status.Active) projStatus = "Active";
      else if (cp.status === Project.Status.OnHold) projStatus = "OnHold";
      else if (cp.status === Project.Status.Done) projStatus = "Done";
      else if (cp.status === Project.Status.Dropped) projStatus = "Dropped";
      r += ` | project="${cp.name}" (${projStatus})`;
    } else {
      r += ` | project=null`;
    }
    r += `\n`;
  }
  if (withOnHold.length > 50) {
    r += `  ... (${withOnHold.length - 50} more)\n`;
  }

  // --- Key analysis ---
  r += `\n--- Key Analysis ---\n`;
  let availableWithOH = 0;
  let nextWithOH = 0;
  let overdueWithOH = 0;
  let blockedWithOH = 0;
  let droppedWithOH = 0;
  for (let i = 0; i < withOnHold.length; i++) {
    const s = withOnHold[i].taskStatus;
    if (s === Task.Status.Available) availableWithOH++;
    if (s === Task.Status.Next) nextWithOH++;
    if (s === Task.Status.Overdue) overdueWithOH++;
    if (s === Task.Status.Blocked) blockedWithOH++;
    if (s === Task.Status.Dropped) droppedWithOH++;
  }
  r += `Available tasks with OnHold tag: ${availableWithOH}\n`;
  r += `Next tasks with OnHold tag: ${nextWithOH}\n`;
  r += `Overdue tasks with OnHold tag: ${overdueWithOH}\n`;
  r += `Blocked tasks with OnHold tag: ${blockedWithOH}\n`;
  r += `Dropped tasks with OnHold tag: ${droppedWithOH}\n`;
  r += `\n`;
  r += `If Available/Next/Overdue counts are 0 → OnHold tags DO cause blocking.\n`;
  r += `If they are > 0 → OnHold tags do NOT affect taskStatus directly.\n`;

  return r;
})();
