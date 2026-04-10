// 01b — Floating Timezone Probe
// WRITES TO OMNIFOCUS DATABASE (creates one test task with notifications)
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Creates a task with a summer (BST) dueDate, adds two due-relative notifications,
// then snapshots everything across floating=true → false → true.
//
// Answers: What changes (if anything) when shouldUseFloatingTimeZone is toggled?
// Also gives us a BST-period date to inspect (script 01 only sampled a GMT date).
//
// CAVEAT: This test runs from the same timezone where the task is created.
// Cross-timezone behavior is NOT tested here.

(() => {
  let r = `=== 01b: Floating Timezone Probe ===\n\n`;

  // --- Create test task with a BST-period dueDate ---
  const task = new Task("TZ-PROBE-Floating");
  task.dueDate = new Date("2026-07-15T10:00:00Z");  // July = BST, 10:00 UTC = 11:00 BST

  // Add two due-relative notifications
  task.addNotification(-60);       // 1 minute before due
  task.addNotification(-86400);    // 1 day before due

  r += `Created: "${task.name}" (id: ${task.id.primaryKey})\n`;
  r += `Input dueDate: new Date("2026-07-15T10:00:00Z")\n`;
  r += `Notifications added: -60min (1min before due), -86400min (1 day before due)\n\n`;

  // --- Helper to snapshot all date + notification properties ---
  function snapshot(label) {
    r += `  --- ${label} ---\n`;
    r += `  shouldUseFloatingTimeZone: ${task.shouldUseFloatingTimeZone}\n`;

    const dd = task.dueDate;
    if (dd) {
      r += `  dueDate:\n`;
      r += `    toISOString():       ${dd.toISOString()}\n`;
      r += `    getTime():           ${dd.getTime()} (epoch ms)\n`;
      r += `    getTimezoneOffset(): ${dd.getTimezoneOffset()} (min from UTC)\n`;
      r += `    toString():          ${dd.toString()}\n`;
    } else {
      r += `  dueDate: null\n`;
    }

    const edd = task.effectiveDueDate;
    if (edd) {
      r += `  effectiveDueDate:\n`;
      r += `    toISOString():       ${edd.toISOString()}\n`;
      r += `    getTime():           ${edd.getTime()} (epoch ms)\n`;
    } else {
      r += `  effectiveDueDate: null\n`;
    }

    // Notifications
    const notifs = task.notifications;
    r += `  Notifications: ${notifs.length}\n`;
    for (let i = 0; i < notifs.length; i++) {
      const n = notifs[i];
      r += `    [${i}]: kind=${n.kind}`;
      try { r += `, initialFireDate=${n.initialFireDate.toISOString()}`; } catch(e) {}
      try { r += `, relativeFireOffset=${n.relativeFireOffset}min`; } catch(e) {}
      r += `, usesFloatingTimeZone=${n.usesFloatingTimeZone}`;
      r += `, isSnoozed=${n.isSnoozed}`;
      r += `\n`;
    }
    r += `\n`;
  }

  // --- Snapshot as floating (default) ---
  snapshot("FLOATING = true (default)");

  const floatingEpochMs = task.dueDate ? task.dueDate.getTime() : null;
  const floatingISO = task.dueDate ? task.dueDate.toISOString() : null;
  const floatingOffset = task.dueDate ? task.dueDate.getTimezoneOffset() : null;

  // --- Toggle to fixed ---
  task.shouldUseFloatingTimeZone = false;
  snapshot("FLOATING = false (just toggled)");

  const fixedEpochMs = task.dueDate ? task.dueDate.getTime() : null;
  const fixedISO = task.dueDate ? task.dueDate.toISOString() : null;
  const fixedOffset = task.dueDate ? task.dueDate.getTimezoneOffset() : null;

  // --- Toggle back to floating ---
  task.shouldUseFloatingTimeZone = true;
  snapshot("FLOATING = true (restored)");

  const restoredEpochMs = task.dueDate ? task.dueDate.getTime() : null;

  // --- Comparison ---
  r += `--- Comparison ---\n\n`;
  r += `  Epoch ms (floating):  ${floatingEpochMs}\n`;
  r += `  Epoch ms (fixed):     ${fixedEpochMs}\n`;
  r += `  Epoch ms (restored):  ${restoredEpochMs}\n`;
  r += `  floating→fixed delta: ${fixedEpochMs - floatingEpochMs} ms\n`;
  r += `  fixed→restored delta: ${restoredEpochMs - fixedEpochMs} ms\n\n`;
  r += `  ISO (floating): ${floatingISO}\n`;
  r += `  ISO (fixed):    ${fixedISO}\n\n`;
  r += `  TZ offset (floating): ${floatingOffset} min\n`;
  r += `  TZ offset (fixed):    ${fixedOffset} min\n\n`;

  if (floatingEpochMs === fixedEpochMs) {
    r += `  RESULT: Toggling floating does NOT change the underlying Date moment (from same TZ).\n`;
  } else {
    r += `  RESULT: Toggling floating CHANGES the underlying Date moment!\n`;
    r += `    Delta: ${(fixedEpochMs - floatingEpochMs) / 1000}s = ${(fixedEpochMs - floatingEpochMs) / 60000} min\n`;
  }

  r += `\n--- BST Date Offset Check ---\n`;
  r += `  July 15 dueDate getTimezoneOffset: ${floatingOffset} min\n`;
  r += `  (Expected: -60 for BST/UTC+1, or 0 if OmniJS ignores DST)\n`;

  r += `\n--- Cleanup ---\n`;
  r += `  Task "${task.name}" (${task.id.primaryKey}) left in inbox.\n`;
  r += `  Run cleanup.js to delete all TZ-DD-*/TZ-PROBE-* tasks.\n`;

  r += `\n=== END ===\n`;
  return r;
})();
