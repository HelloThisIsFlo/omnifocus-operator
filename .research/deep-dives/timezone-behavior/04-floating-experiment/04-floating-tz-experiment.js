// 04 — Floating Timezone Experiment
// WRITES TO OMNIFOCUS DATABASE
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Prerequisite: Script 03 must have run first (TZ-DD-A through TZ-DD-F exist)
//
// Answers: Q2 (what changes when floating=false), Q7 (toggle on existing task),
//          Q8 (DateComponents with specific timezone)
//
// Parts:
//   1. Find Task A and toggle shouldUseFloatingTimeZone
//   2. Create TZ-DD-G with DateComponents + EST timezone
//   3. Create TZ-DD-H with floating=false from start
//   4. Create TZ-DD-I with date then toggle
//   5. SQLite verification query

(() => {
  let r = `=== 04: Floating Timezone Experiment ===\n\n`;

  // --- Find TZ-DD-A ---
  let taskA = null;
  const tasks = flattenedTasks;
  for (let i = 0; i < tasks.length; i++) {
    if (tasks[i].name.indexOf("TZ-DD-A") === 0) {
      taskA = tasks[i];
      break;
    }
  }

  if (!taskA) {
    return r + "ERROR: TZ-DD-A not found. Run script 03 first.\n";
  }
  r += `Found TZ-DD-A: id=${taskA.id.primaryKey}\n\n`;

  // =========================================================================
  // Part 1: Toggle shouldUseFloatingTimeZone on Task A
  // =========================================================================
  r += `--- Part 1: Toggle Floating on Task A ---\n\n`;

  r += `  BEFORE:\n`;
  r += `    shouldUseFloatingTimeZone: ${taskA.shouldUseFloatingTimeZone}\n`;
  r += `    dueDate.toISOString():     ${taskA.dueDate ? taskA.dueDate.toISOString() : 'null'}\n`;
  r += `    dueDate.getTime():         ${taskA.dueDate ? taskA.dueDate.getTime() : 'null'} (epoch ms)\n`;
  r += `    dueDate.toString():        ${taskA.dueDate ? taskA.dueDate.toString() : 'null'}\n\n`;

  // Toggle to false
  taskA.shouldUseFloatingTimeZone = false;

  r += `  AFTER (set to false):\n`;
  r += `    shouldUseFloatingTimeZone: ${taskA.shouldUseFloatingTimeZone}\n`;
  r += `    dueDate.toISOString():     ${taskA.dueDate ? taskA.dueDate.toISOString() : 'null'}\n`;
  r += `    dueDate.getTime():         ${taskA.dueDate ? taskA.dueDate.getTime() : 'null'} (epoch ms)\n`;
  r += `    dueDate.toString():        ${taskA.dueDate ? taskA.dueDate.toString() : 'null'}\n\n`;

  // Check: did the underlying moment change?
  r += `  KEY QUESTION: Did getTime() change? `;
  // (We logged both — user/agent will compare the before/after values)
  r += `Compare BEFORE and AFTER getTime() values above.\n\n`;

  // Toggle back to true for completeness
  taskA.shouldUseFloatingTimeZone = true;
  r += `  RESTORED: shouldUseFloatingTimeZone = ${taskA.shouldUseFloatingTimeZone}\n`;
  r += `    dueDate.getTime(): ${taskA.dueDate ? taskA.dueDate.getTime() : 'null'}\n\n`;

  // =========================================================================
  // Part 2: Create TZ-DD-G with DateComponents + EST timezone
  // =========================================================================
  r += `--- Part 2: TZ-DD-G — DateComponents with EST ---\n\n`;

  try {
    const dc = new DateComponents();
    dc.year = 2026;
    dc.month = 7;
    dc.day = 15;
    dc.hour = 9;
    dc.minute = 0;
    dc.second = 0;
    dc.timeZone = new TimeZone("EST");

    r += `  DateComponents created:\n`;
    r += `    year=${dc.year}, month=${dc.month}, day=${dc.day}, hour=${dc.hour}\n`;
    r += `    timeZone=${dc.timeZone}, abbreviation=${dc.timeZone.abbreviation}\n`;
    r += `    secondsFromGMT=${dc.timeZone.secondsFromGMT}\n\n`;

    const estDate = Calendar.current.dateFromDateComponents(dc);
    r += `  Date from DateComponents:\n`;
    r += `    toISOString(): ${estDate.toISOString()}\n`;
    r += `    getTime():     ${estDate.getTime()}\n`;
    r += `    Expected:      09:00 EST = 14:00 UTC = 2026-07-15T14:00:00.000Z\n\n`;

    const taskG = new Task("TZ-DD-G: DateComponents EST");
    taskG.dueDate = estDate;
    taskG.shouldUseFloatingTimeZone = false;

    r += `  Task created:\n`;
    r += `    id:       ${taskG.id.primaryKey}\n`;
    r += `    dueDate:  ${taskG.dueDate.toISOString()}\n`;
    r += `    floating: ${taskG.shouldUseFloatingTimeZone}\n\n`;
  } catch (e) {
    r += `  ERROR creating TZ-DD-G: ${e.message}\n\n`;
  }

  // =========================================================================
  // Part 3: Create TZ-DD-H — Non-floating from start
  // =========================================================================
  r += `--- Part 3: TZ-DD-H — Non-floating from start ---\n\n`;

  try {
    const taskH = new Task("TZ-DD-H: Non-floating from start");
    taskH.shouldUseFloatingTimeZone = false;
    taskH.dueDate = new Date("2026-07-15T09:00:00Z");

    r += `  Task created (set floating=false BEFORE dueDate):\n`;
    r += `    id:       ${taskH.id.primaryKey}\n`;
    r += `    dueDate:  ${taskH.dueDate.toISOString()}\n`;
    r += `    getTime(): ${taskH.dueDate.getTime()}\n`;
    r += `    floating: ${taskH.shouldUseFloatingTimeZone}\n\n`;
  } catch (e) {
    r += `  ERROR creating TZ-DD-H: ${e.message}\n\n`;
  }

  // =========================================================================
  // Part 4: Create TZ-DD-I — Date then toggle
  // =========================================================================
  r += `--- Part 4: TZ-DD-I — Set date then toggle floating ---\n\n`;

  try {
    const taskI = new Task("TZ-DD-I: Date then toggle");
    taskI.dueDate = new Date("2026-07-15T09:00:00Z");

    r += `  After setting dueDate (floating still true):\n`;
    r += `    dueDate:  ${taskI.dueDate.toISOString()}\n`;
    r += `    getTime(): ${taskI.dueDate.getTime()}\n`;
    r += `    floating: ${taskI.shouldUseFloatingTimeZone}\n\n`;

    taskI.shouldUseFloatingTimeZone = false;

    r += `  After toggling floating to false:\n`;
    r += `    dueDate:  ${taskI.dueDate.toISOString()}\n`;
    r += `    getTime(): ${taskI.dueDate.getTime()}\n`;
    r += `    floating: ${taskI.shouldUseFloatingTimeZone}\n\n`;

    r += `  Task:\n`;
    r += `    id: ${taskI.id.primaryKey}\n\n`;
  } catch (e) {
    r += `  ERROR creating TZ-DD-I: ${e.message}\n\n`;
  }

  // =========================================================================
  // Part 5: H vs I comparison
  // =========================================================================
  r += `--- Part 5: H vs I Comparison ---\n\n`;
  r += `  Both got dueDate = new Date("2026-07-15T09:00:00Z")\n`;
  r += `  H: set floating=false BEFORE dueDate\n`;
  r += `  I: set dueDate BEFORE floating=false\n`;
  r += `  Compare their getTime() values above — are they identical?\n\n`;

  // =========================================================================
  // Part 6: SQLite verification query
  // =========================================================================
  r += `--- Part 6: SQLite Verification Query ---\n\n`;
  r += `  Run this after the script completes:\n\n`;
  r += `  sqlite3 -readonly -header -column \\\n`;
  r += `    ~/Library/Group\\ Containers/34YW5XSRB7.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel/OmniFocusDatabase.db \\\n`;
  r += `    "SELECT persistentIdentifier, name, dateDue, effectiveDateDue, shouldUseFloatingTimeZone FROM Task WHERE name LIKE 'TZ-DD-%'"\n\n`;

  // =========================================================================
  // Summary of new task IDs
  // =========================================================================
  r += `--- New Task IDs ---\n\n`;
  const tzTasks = [];
  for (let i = 0; i < tasks.length; i++) {
    const t = tasks[i];
    if (t.name.indexOf("TZ-DD-") === 0) {
      tzTasks.push(t);
    }
  }
  for (const t of tzTasks) {
    r += `  ${t.name}: id=${t.id.primaryKey}, floating=${t.shouldUseFloatingTimeZone}\n`;
  }

  r += `\n=== END ===\n`;
  return r;
})();
