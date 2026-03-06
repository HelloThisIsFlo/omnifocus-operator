// 20 — Inbox Task Audit
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Detailed analysis of inbox tasks (inInbox=true).
// Status distribution, relationships, boolean fields, dates, tags.

(() => {
  let r = `=== 20: Inbox Task Audit ===\n\n`;

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

  const tasks = flattenedTasks;
  const inbox = [];
  const nonInbox = [];

  for (let i = 0; i < tasks.length; i++) {
    if (tasks[i].inInbox) {
      inbox.push(tasks[i]);
    } else {
      nonInbox.push(tasks[i]);
    }
  }

  r += `Inbox tasks: ${inbox.length}\n`;
  r += `Non-inbox tasks: ${nonInbox.length}\n\n`;

  // --- Status distribution ---
  r += `--- Inbox Status Distribution ---\n`;
  const statusCounts = {};
  for (let i = 0; i < inbox.length; i++) {
    const s = resolveTaskStatus(inbox[i]);
    statusCounts[s] = (statusCounts[s] || 0) + 1;
  }
  const sKeys = Object.keys(statusCounts).sort();
  for (let i = 0; i < sKeys.length; i++) {
    r += `  ${sKeys[i]}: ${statusCounts[sKeys[i]]}\n`;
  }

  // --- Relationships ---
  r += `\n--- Inbox Relationships ---\n`;
  let cpNull = 0, cpPresent = 0;
  let parentNull = 0, parentPresent = 0;
  let acNull = 0, acPresent = 0;
  for (let i = 0; i < inbox.length; i++) {
    const t = inbox[i];
    if (t.containingProject) cpPresent++; else cpNull++;
    if (t.parent) parentPresent++; else parentNull++;
    if (t.assignedContainer) acPresent++; else acNull++;
  }
  r += `  containingProject: present=${cpPresent}, null=${cpNull}\n`;
  r += `  parent: present=${parentPresent}, null=${parentNull}\n`;
  r += `  assignedContainer: present=${acPresent}, null=${acNull}\n`;

  // --- Boolean fields ---
  r += `\n--- Inbox Boolean Fields ---\n`;
  let activeT=0, activeF=0, effActiveT=0, effActiveF=0;
  let flaggedT=0, flaggedF=0, seqT=0, seqF=0;
  let hasChildT=0, hasChildF=0, cbcT=0, cbcF=0;
  for (let i = 0; i < inbox.length; i++) {
    const t = inbox[i];
    if (t.active) activeT++; else activeF++;
    if (t.effectiveActive) effActiveT++; else effActiveF++;
    if (t.flagged) flaggedT++; else flaggedF++;
    if (t.sequential) seqT++; else seqF++;
    if (t.hasChildren) hasChildT++; else hasChildF++;
    if (t.completedByChildren) cbcT++; else cbcF++;
  }
  r += `  active: true=${activeT}, false=${activeF}\n`;
  r += `  effectiveActive: true=${effActiveT}, false=${effActiveF}\n`;
  r += `  flagged: true=${flaggedT}, false=${flaggedF}\n`;
  r += `  sequential: true=${seqT}, false=${seqF}\n`;
  r += `  hasChildren: true=${hasChildT}, false=${hasChildF}\n`;
  r += `  completedByChildren: true=${cbcT}, false=${cbcF}\n`;

  // --- Date fields ---
  r += `\n--- Inbox Date Fields ---\n`;
  let dueP=0, deferP=0, effDueP=0, effDeferP=0;
  for (let i = 0; i < inbox.length; i++) {
    const t = inbox[i];
    if (t.dueDate) dueP++;
    if (t.deferDate) deferP++;
    if (t.effectiveDueDate) effDueP++;
    if (t.effectiveDeferDate) effDeferP++;
  }
  r += `  dueDate: present=${dueP}, null=${inbox.length - dueP}\n`;
  r += `  deferDate: present=${deferP}, null=${inbox.length - deferP}\n`;
  r += `  effectiveDueDate: present=${effDueP}, null=${inbox.length - effDueP}\n`;
  r += `  effectiveDeferDate: present=${effDeferP}, null=${inbox.length - effDeferP}\n`;

  // --- Tags ---
  r += `\n--- Inbox Tags ---\n`;
  let zeroTags=0, oneTags=0, multiTags=0;
  for (let i = 0; i < inbox.length; i++) {
    const c = inbox[i].tags.length;
    if (c === 0) zeroTags++;
    else if (c === 1) oneTags++;
    else multiTags++;
  }
  r += `  zero tags: ${zeroTags}, one tag: ${oneTags}, multi tags: ${multiTags}\n`;

  // --- Detailed list (first 20) ---
  r += `\n--- Inbox Tasks (first 20) ---\n`;
  const showCount = Math.min(inbox.length, 20);
  for (let i = 0; i < showCount; i++) {
    const t = inbox[i];
    r += `  "${t.name}" | ${resolveTaskStatus(t)}`;
    r += ` | active=${t.active} | effActive=${t.effectiveActive}`;
    if (t.dueDate) r += ` | due=${t.dueDate.toISOString().slice(0,10)}`;
    if (t.deferDate) r += ` | defer=${t.deferDate.toISOString().slice(0,10)}`;
    if (t.tags.length > 0) {
      const tagNames = [];
      for (let j = 0; j < t.tags.length; j++) tagNames.push(t.tags[j].name);
      r += ` | tags=[${tagNames.join(", ")}]`;
    }
    r += `\n`;
  }

  return r;
})();
