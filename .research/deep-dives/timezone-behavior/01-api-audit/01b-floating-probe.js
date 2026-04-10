// 01b — Floating vs Fixed Probe (Baseline)
// WRITES TO OMNIFOCUS DATABASE (creates two test tasks)
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Creates TWO tasks with identical dueDate:
//   - TZ-PROBE-Floating: shouldUseFloatingTimeZone = true (default)
//   - TZ-PROBE-Fixed:    shouldUseFloatingTimeZone = false
//
// Run this in your HOME timezone first to capture the baseline.
// Then switch timezone and run 01c to compare.

(() => {
  let r = `=== 01b: Floating vs Fixed Probe (Baseline) ===\n\n`;

  const DUE = "2026-07-15T10:00:00Z";  // July = BST, 10:00 UTC = 11:00 BST

  // --- Create floating task ---
  const floating = new Task("TZ-PROBE-Floating");
  floating.dueDate = new Date(DUE);
  floating.addNotification(-60);       // 1 minute before due
  floating.addNotification(-86400);    // 1 day before due
  // shouldUseFloatingTimeZone defaults to true

  // --- Create fixed task ---
  const fixed = new Task("TZ-PROBE-Fixed");
  fixed.dueDate = new Date(DUE);
  fixed.addNotification(-60);          // 1 minute before due
  fixed.addNotification(-86400);       // 1 day before due
  fixed.shouldUseFloatingTimeZone = false;

  r += `Created two tasks with identical dueDate: new Date("${DUE}")\n`;
  r += `Both have notifications: -60min (1min before), -86400min (1 day before)\n\n`;

  // --- Helper ---
  function snapshot(label, task) {
    r += `  --- ${label} ---\n`;
    r += `  name:     ${task.name}\n`;
    r += `  id:       ${task.id.primaryKey}\n`;
    r += `  floating: ${task.shouldUseFloatingTimeZone}\n`;

    const dd = task.dueDate;
    if (dd) {
      r += `  dueDate:\n`;
      r += `    toISOString():       ${dd.toISOString()}\n`;
      r += `    getTime():           ${dd.getTime()} (epoch ms)\n`;
      r += `    getTimezoneOffset(): ${dd.getTimezoneOffset()} (min from UTC)\n`;
      r += `    toString():          ${dd.toString()}\n`;
    }

    const edd = task.effectiveDueDate;
    if (edd) {
      r += `  effectiveDueDate:\n`;
      r += `    toISOString():       ${edd.toISOString()}\n`;
      r += `    getTime():           ${edd.getTime()} (epoch ms)\n`;
    }

    const notifs = task.notifications;
    r += `  Notifications: ${notifs.length}\n`;
    for (let i = 0; i < notifs.length; i++) {
      const n = notifs[i];
      r += `    [${i}]: kind=${n.kind}`;
      try { r += `, initialFireDate=${n.initialFireDate.toISOString()}`; } catch(e) {}
      try { r += `, relativeFireOffset=${n.relativeFireOffset}min`; } catch(e) {}
      r += `, usesFloatingTimeZone=${n.usesFloatingTimeZone}`;
      r += `\n`;
    }
    r += `\n`;
  }

  snapshot("FLOATING (shouldUseFloatingTimeZone = true)", floating);
  snapshot("FIXED (shouldUseFloatingTimeZone = false)", fixed);

  // --- Comparison ---
  r += `--- Baseline Comparison ---\n\n`;

  const fEpoch = floating.dueDate.getTime();
  const xEpoch = fixed.dueDate.getTime();

  r += `  Floating getTime(): ${fEpoch}\n`;
  r += `  Fixed    getTime(): ${xEpoch}\n`;
  r += `  Delta:              ${xEpoch - fEpoch} ms\n\n`;

  r += `  Floating toISOString(): ${floating.dueDate.toISOString()}\n`;
  r += `  Fixed    toISOString(): ${fixed.dueDate.toISOString()}\n\n`;

  if (fEpoch === xEpoch) {
    r += `  RESULT: Both tasks have identical Date moments in home timezone.\n`;
    r += `    Any difference in 01c (cross-timezone) proves the flag matters.\n`;
  } else {
    r += `  RESULT: Tasks already differ in home timezone! Delta=${(xEpoch - fEpoch) / 60000} min\n`;
  }

  r += `\n--- Cleanup ---\n`;
  r += `  Tasks left in inbox: TZ-PROBE-Floating, TZ-PROBE-Fixed\n`;
  r += `  Run cleanup.js to delete all TZ-PROBE-* tasks.\n`;

  r += `\n=== END ===\n`;
  return r;
})();
