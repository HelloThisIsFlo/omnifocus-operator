// 05 — [WRITE] Create Test Data (Comprehensive)
// WRITES TO OMNIFOCUS DATABASE
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Creates a comprehensive hierarchy of test entities covering all status
// combinations, blocking scenarios, and edge cases. Every entity is tagged
// "API Audit" for easy cleanup via Script 08.
//
// Test projects created:
//   1. Parallel Project — tasks in every status (Available, Overdue, DueSoon, Blocked-by-defer, Flagged, Estimated, Completed, Dropped)
//   2. Sequential Project — Next/Blocked ordering, Overdue-masks-Blocked test
//   3. OnHold Project — effect of OnHold on child task statuses
//   4. Dropped Project — effect of Dropped on child task statuses
//   5. Nested Groups — parallel project with sequential action group (parent/child blocking)
//   6. CompletedByChildren — auto-completion behavior test
//   7. Deep Nesting — grandparent > parent > child inheritance
//   8. Parent Blocked by Children — parent task with incomplete children

(() => {
  let r = `=== 05: [WRITE] Create Test Data (Comprehensive) ===\n\n`;

  // --- Date helpers ---
  function daysFromNow(n) {
    const d = new Date();
    d.setDate(d.getDate() + n);
    d.setHours(17, 0, 0, 0);
    return d;
  }
  function hoursFromNow(n) {
    const d = new Date();
    d.setHours(d.getHours() + n);
    d.setMinutes(0, 0, 0);
    return d;
  }

  // --- Create audit tag ---
  r += `Creating tag "API Audit"...\n`;
  const tag = new Tag("API Audit");
  r += `  Tag created: id=${tag.id.primaryKey}\n\n`;

  function tagIt(entity) {
    entity.addTag(tag);
  }

  function reportTask(task, indent) {
    const pad = " ".repeat(indent);
    r += `${pad}${task.name}: id=${task.id.primaryKey}, taskStatus=${statusStr(task)}\n`;
  }

  // Status resolver for reporting
  function statusStr(task) {
    const s = task.taskStatus;
    if (s === Task.Status.Available) return "Available";
    if (s === Task.Status.Blocked) return "Blocked";
    if (s === Task.Status.Completed) return "Completed";
    if (s === Task.Status.Dropped) return "Dropped";
    if (s === Task.Status.DueSoon) return "DueSoon";
    if (s === Task.Status.Next) return "Next";
    if (s === Task.Status.Overdue) return "Overdue";
    return "UNKNOWN";
  }

  function projStatusStr(proj) {
    const s = proj.status;
    if (s === Project.Status.Active) return "Active";
    if (s === Project.Status.OnHold) return "OnHold";
    if (s === Project.Status.Done) return "Done";
    if (s === Project.Status.Dropped) return "Dropped";
    return "UNKNOWN";
  }

  // =========================================================================
  // 1. PARALLEL PROJECT — one task per interesting status
  // =========================================================================
  r += `--- 1. Parallel Project (all statuses) ---\n`;
  const pp = new Project("Audit: Parallel Project");
  pp.note = "Parallel project with tasks covering every status.";
  tagIt(pp);

  // Available: no blocking conditions, no due date
  const tAvail = new Task("Available Task", pp);
  tAvail.note = "Should be Available — no blocking.";
  tagIt(tAvail);

  // Overdue: due date in the past
  const tOverdue = new Task("Overdue Task", pp);
  tOverdue.dueDate = daysFromNow(-3);
  tOverdue.note = "Should be Overdue — due 3 days ago.";
  tagIt(tOverdue);

  // DueSoon: due date today (within threshold)
  const tDueSoon = new Task("DueSoon Task", pp);
  tDueSoon.dueDate = hoursFromNow(6);
  tDueSoon.note = "Should be DueSoon — due in 6 hours.";
  tagIt(tDueSoon);

  // Blocked by defer: future defer date
  const tDeferred = new Task("Blocked by Defer", pp);
  tDeferred.deferDate = daysFromNow(10);
  tDeferred.note = "Should be Blocked — deferred 10 days from now.";
  tagIt(tDeferred);

  // Flagged task: flagged but otherwise available
  const tFlagged = new Task("Flagged Task", pp);
  tFlagged.flagged = true;
  tFlagged.note = "Should be Available — flagged doesn't change status.";
  tagIt(tFlagged);

  // With estimate
  const tEstimate = new Task("Task with Estimate", pp);
  tEstimate.estimatedMinutes = 30;
  tEstimate.note = "Should be Available — has 30min estimate.";
  tagIt(tEstimate);

  // Completed task
  const tCompleted = new Task("Completed Task", pp);
  tCompleted.note = "Will be marked complete.";
  tagIt(tCompleted);
  tCompleted.markComplete();

  // Dropped task
  const tDropped = new Task("Dropped Task", pp);
  tDropped.note = "Will be dropped.";
  tagIt(tDropped);
  tDropped.drop(true);

  // Overdue AND deferred in the past (defer < now < due... wait, due is past too)
  // This tests: past defer + past due = Overdue (defer no longer blocks)
  const tOverduePastDefer = new Task("Overdue with Past Defer", pp);
  tOverduePastDefer.deferDate = daysFromNow(-10);
  tOverduePastDefer.dueDate = daysFromNow(-2);
  tOverduePastDefer.note = "Should be Overdue — defer is in the past, due is in the past.";
  tagIt(tOverduePastDefer);

  // Overdue AND deferred in future (tests: does defer block override overdue?)
  const tOverdueFutureDefer = new Task("Overdue + Future Defer", pp);
  tOverdueFutureDefer.dueDate = daysFromNow(-2);
  tOverdueFutureDefer.deferDate = daysFromNow(5);
  tOverdueFutureDefer.note = "Interesting: past due BUT future defer. Blocked or Overdue?";
  tagIt(tOverdueFutureDefer);

  r += `  Project: ${pp.name} (id=${pp.id.primaryKey}, status=${projStatusStr(pp)})\n`;
  const ppTasks = pp.task.children;
  for (const t of ppTasks) reportTask(t, 4);

  // =========================================================================
  // 2. SEQUENTIAL PROJECT — Next/Blocked ordering + Overdue masking
  // =========================================================================
  r += `\n--- 2. Sequential Project (ordering + Overdue masking) ---\n`;
  const sp = new Project("Audit: Sequential Project");
  sp.sequential = true;
  sp.note = "Sequential project — only first incomplete should be Next.";
  tagIt(sp);

  const sTask1 = new Task("Seq Task 1 (first)", sp);
  sTask1.note = "Should be Next — first incomplete in sequential project.";
  tagIt(sTask1);

  const sTask2 = new Task("Seq Task 2 (second)", sp);
  sTask2.note = "Should be Blocked — waiting for Task 1.";
  tagIt(sTask2);

  const sTask3 = new Task("Seq Task 3 (overdue, third)", sp);
  sTask3.dueDate = daysFromNow(-5);
  sTask3.note = "KEY TEST: past due + sequential blocked. Overdue or Blocked?";
  tagIt(sTask3);

  const sTask4 = new Task("Seq Task 4 (due soon, fourth)", sp);
  sTask4.dueDate = hoursFromNow(4);
  sTask4.note = "Past due soon threshold + sequential blocked. DueSoon or Blocked?";
  tagIt(sTask4);

  r += `  Project: ${sp.name} (id=${sp.id.primaryKey}, sequential=${sp.sequential})\n`;
  for (const t of sp.task.children) reportTask(t, 4);

  // =========================================================================
  // 3. ON HOLD PROJECT — does OnHold affect child task status?
  // =========================================================================
  r += `\n--- 3. OnHold Project ---\n`;
  const ohp = new Project("Audit: OnHold Project");
  ohp.note = "Project set to OnHold — what happens to child task statuses?";
  tagIt(ohp);

  const ohTask1 = new Task("Task in OnHold Project (no due)", ohp);
  ohTask1.note = "What status? Available? Blocked? Something else?";
  tagIt(ohTask1);

  const ohTask2 = new Task("Overdue in OnHold Project", ohp);
  ohTask2.dueDate = daysFromNow(-3);
  ohTask2.note = "Past due in OnHold project — Overdue or does OnHold override?";
  tagIt(ohTask2);

  // Set to OnHold AFTER creating tasks
  ohp.status = Project.Status.OnHold;

  r += `  Project: ${ohp.name} (id=${ohp.id.primaryKey}, status=${projStatusStr(ohp)})\n`;
  r += `    task.active=${ohp.task.active}, task.effectiveActive=${ohp.task.effectiveActive}\n`;
  for (const t of ohp.task.children) {
    r += `    ${t.name}: taskStatus=${statusStr(t)}, active=${t.active}, effectiveActive=${t.effectiveActive}\n`;
  }

  // =========================================================================
  // 4. DROPPED PROJECT — does Dropped propagate to children?
  // =========================================================================
  r += `\n--- 4. Dropped Project ---\n`;
  const dp = new Project("Audit: Dropped Project");
  dp.note = "Project set to Dropped — children should inherit?";
  tagIt(dp);

  const dpTask1 = new Task("Task in Dropped Project", dp);
  dpTask1.note = "Should this become Dropped?";
  tagIt(dpTask1);

  const dpTask2 = new Task("Overdue in Dropped Project", dp);
  dpTask2.dueDate = daysFromNow(-2);
  dpTask2.note = "Past due in Dropped project — Overdue or Dropped?";
  tagIt(dpTask2);

  // Drop the project
  dp.status = Project.Status.Dropped;

  r += `  Project: ${dp.name} (id=${dp.id.primaryKey}, status=${projStatusStr(dp)})\n`;
  r += `    task.active=${dp.task.active}, task.effectiveActive=${dp.task.effectiveActive}\n`;
  for (const t of dp.task.children) {
    r += `    ${t.name}: taskStatus=${statusStr(t)}, active=${t.active}, effectiveActive=${t.effectiveActive}\n`;
  }

  // =========================================================================
  // 5. NESTED GROUPS — parallel project with sequential action group
  // =========================================================================
  r += `\n--- 5. Nested Groups (action group inside parallel project) ---\n`;
  const ngp = new Project("Audit: Nested Groups");
  ngp.note = "Parallel project with a sequential action group inside.";
  tagIt(ngp);

  // Regular task at project level (should be Available)
  const ngAvail = new Task("Top-level Available", ngp);
  ngAvail.note = "Should be Available — parallel project, no blocking.";
  tagIt(ngAvail);

  // Sequential action group (a task with children, sequential=true)
  const ngGroup = new Task("Sequential Action Group", ngp);
  ngGroup.sequential = true;
  ngGroup.note = "This is a parent task acting as a sequential action group.";
  tagIt(ngGroup);

  const ngChild1 = new Task("Group Child 1", ngGroup);
  ngChild1.note = "Should be Next — first in sequential group.";
  tagIt(ngChild1);

  const ngChild2 = new Task("Group Child 2", ngGroup);
  ngChild2.note = "Should be Blocked — sequential, waiting for Child 1.";
  tagIt(ngChild2);

  const ngChild3 = new Task("Group Child 3 (overdue)", ngGroup);
  ngChild3.dueDate = daysFromNow(-1);
  ngChild3.note = "Past due + sequential blocked. Overdue or Blocked?";
  tagIt(ngChild3);

  // Parallel action group for comparison
  const ngParGroup = new Task("Parallel Action Group", ngp);
  ngParGroup.sequential = false;
  ngParGroup.note = "Parent task as parallel action group.";
  tagIt(ngParGroup);

  const ngParChild1 = new Task("Parallel Child 1", ngParGroup);
  ngParChild1.note = "Should be Available — parallel group.";
  tagIt(ngParChild1);

  const ngParChild2 = new Task("Parallel Child 2 (overdue)", ngParGroup);
  ngParChild2.dueDate = daysFromNow(-1);
  ngParChild2.note = "Should be Overdue — parallel, no sequential blocking.";
  tagIt(ngParChild2);

  r += `  Project: ${ngp.name} (id=${ngp.id.primaryKey})\n`;
  for (const t of ngp.task.children) {
    reportTask(t, 4);
    if (t.hasChildren) {
      for (const c of t.children) reportTask(c, 8);
    }
  }

  // =========================================================================
  // 6. COMPLETED BY CHILDREN — auto-completion test
  // =========================================================================
  r += `\n--- 6. CompletedByChildren Test ---\n`;
  const cbcp = new Project("Audit: CompletedByChildren");
  cbcp.note = "All children will be completed — does parent auto-complete?";
  tagIt(cbcp);

  const cbcTask1 = new Task("CBC Child 1", cbcp);
  cbcTask1.note = "Will be completed.";
  tagIt(cbcTask1);

  const cbcTask2 = new Task("CBC Child 2", cbcp);
  cbcTask2.note = "Will be completed.";
  tagIt(cbcTask2);

  // Verify completedByChildren default first
  r += `  Project completedByChildren BEFORE: ${cbcp.completedByChildren}\n`;

  // Complete both children
  cbcTask1.markComplete();
  cbcTask2.markComplete();

  r += `  After completing both children:\n`;
  r += `    Project status: ${projStatusStr(cbcp)}\n`;
  r += `    Project completed: ${cbcp.completed}\n`;
  r += `    task.taskStatus: ${statusStr(cbcp.task)}\n`;

  // =========================================================================
  // 7. DEEP NESTING — grandparent > parent > child date/status inheritance
  // =========================================================================
  r += `\n--- 7. Deep Nesting (3 levels) ---\n`;
  const dnp = new Project("Audit: Deep Nesting");
  dnp.dueDate = daysFromNow(14);
  dnp.note = "Project with due date — do children inherit effectiveDueDate?";
  tagIt(dnp);

  // Parent task (with its own due date)
  const dnParent = new Task("Level 1 Parent", dnp);
  dnParent.dueDate = daysFromNow(7);
  dnParent.note = "Has own due date — children should inherit this, not project's.";
  tagIt(dnParent);

  // Child of parent (no own due date — should inherit from parent)
  const dnChild = new Task("Level 2 Child (no due)", dnParent);
  dnChild.note = "No due date — effectiveDueDate should come from parent.";
  tagIt(dnChild);

  // Grandchild (no own due date)
  const dnGrandchild = new Task("Level 3 Grandchild (no due)", dnChild);
  dnGrandchild.note = "No due date — effectiveDueDate from nearest ancestor with one.";
  tagIt(dnGrandchild);

  // Another child with its OWN EARLIER due date (should use own)
  const dnChildOwn = new Task("Level 2 Child (own earlier due)", dnParent);
  dnChildOwn.dueDate = daysFromNow(3);
  dnChildOwn.note = "Own due (day+3) is earlier than parent (day+7). Should use own.";
  tagIt(dnChildOwn);

  // KEY TEST: child with LATER due date than parent
  // If "own value wins" → effectiveDueDate = day+20 (child's own)
  // If "soonest wins" → effectiveDueDate = day+7 (parent's, because it's earlier)
  const dnChildLater = new Task("Level 2 Child (own LATER due)", dnParent);
  dnChildLater.dueDate = daysFromNow(20);
  dnChildLater.note = "Own due (day+20) is LATER than parent (day+7). Soonest wins or own wins?";
  tagIt(dnChildLater);

  // Sibling at project level with no due (inherits from project)
  const dnSibling = new Task("Level 1 Sibling (no due)", dnp);
  dnSibling.note = "No due date, no parent task — effectiveDueDate from project.";
  tagIt(dnSibling);

  r += `  Project: ${dnp.name} (dueDate=${dnp.dueDate})\n`;
  r += `  Project effectiveDueDate: ${dnp.effectiveDueDate}\n`;
  const reportDeep = (t, indent) => {
    const pad = " ".repeat(indent);
    r += `${pad}${t.name}: dueDate=${t.dueDate}, effectiveDueDate=${t.effectiveDueDate}, taskStatus=${statusStr(t)}\n`;
    if (t.hasChildren) {
      for (const c of t.children) reportDeep(c, indent + 4);
    }
  };
  for (const t of dnp.task.children) reportDeep(t, 4);

  // =========================================================================
  // 8. PARENT BLOCKED BY CHILDREN — incomplete children block parent
  // =========================================================================
  r += `\n--- 8. Parent Blocked by Children ---\n`;
  const pbcp = new Project("Audit: Parent Blocked");
  pbcp.note = "Testing whether parent tasks with children get Blocked status.";
  tagIt(pbcp);

  // Parent with children (parallel) — should parent be Available or Blocked?
  const pbParallel = new Task("Parent (parallel, has children)", pbcp);
  pbParallel.sequential = false;
  pbParallel.note = "Parallel parent with incomplete children.";
  tagIt(pbParallel);

  const pbPChild1 = new Task("Parallel Parent Child 1", pbParallel);
  tagIt(pbPChild1);
  const pbPChild2 = new Task("Parallel Parent Child 2", pbParallel);
  tagIt(pbPChild2);

  // Parent with children (sequential)
  const pbSequential = new Task("Parent (sequential, has children)", pbcp);
  pbSequential.sequential = true;
  pbSequential.note = "Sequential parent with incomplete children.";
  tagIt(pbSequential);

  const pbSChild1 = new Task("Sequential Parent Child 1", pbSequential);
  tagIt(pbSChild1);
  const pbSChild2 = new Task("Sequential Parent Child 2", pbSequential);
  tagIt(pbSChild2);

  // Parent with overdue due date and incomplete children
  const pbOverdue = new Task("Overdue Parent (has children)", pbcp);
  pbOverdue.dueDate = daysFromNow(-2);
  pbOverdue.note = "Parent is overdue but has incomplete children. Overdue or Blocked?";
  tagIt(pbOverdue);

  const pbOChild1 = new Task("Overdue Parent Child 1", pbOverdue);
  tagIt(pbOChild1);

  // Parent with all children complete
  const pbAllDone = new Task("Parent (all children complete)", pbcp);
  pbAllDone.completedByChildren = true;
  pbAllDone.note = "All children complete — does parent auto-complete?";
  tagIt(pbAllDone);

  const pbDChild1 = new Task("Done Child 1", pbAllDone);
  tagIt(pbDChild1);
  pbDChild1.markComplete();
  const pbDChild2 = new Task("Done Child 2", pbAllDone);
  tagIt(pbDChild2);
  pbDChild2.markComplete();

  // Parent with completedByChildren=false and all children complete
  const pbNoCBC = new Task("Parent (CBC=false, all children complete)", pbcp);
  pbNoCBC.completedByChildren = false;
  pbNoCBC.note = "CBC=false, all children complete — should NOT auto-complete.";
  tagIt(pbNoCBC);

  const pbNCChild1 = new Task("NoCBC Child 1", pbNoCBC);
  tagIt(pbNCChild1);
  pbNCChild1.markComplete();
  const pbNCChild2 = new Task("NoCBC Child 2", pbNoCBC);
  tagIt(pbNCChild2);
  pbNCChild2.markComplete();

  r += `  Project: ${pbcp.name} (id=${pbcp.id.primaryKey})\n`;
  const reportBlocked = (t, indent) => {
    const pad = " ".repeat(indent);
    const extra = t.hasChildren ? `, completedByChildren=${t.completedByChildren}, completed=${t.completed}` : "";
    r += `${pad}${t.name}: taskStatus=${statusStr(t)}, active=${t.active}, effectiveActive=${t.effectiveActive}${extra}\n`;
    if (t.hasChildren) {
      for (const c of t.children) reportBlocked(c, indent + 4);
    }
  };
  for (const t of pbcp.task.children) reportBlocked(t, 4);

  // =========================================================================
  // SUMMARY
  // =========================================================================
  r += `\n\n=== SUMMARY ===\n`;
  r += `Tag: "API Audit" (id: ${tag.id.primaryKey})\n`;
  r += `Projects created: 8\n`;

  // Count all tagged tasks
  let totalTasks = 0;
  for (const t of flattenedTasks) {
    if (t.tags.some(tg => tg.name === "API Audit")) totalTasks++;
  }
  r += `Tasks created: ${totalTasks} (all tagged "API Audit")\n`;
  r += `\nAll entities tagged with "API Audit" for easy cleanup (Script 08).\n`;

  return r;
})();
