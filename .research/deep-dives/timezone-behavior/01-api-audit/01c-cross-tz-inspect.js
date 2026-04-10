// 01c — Cross-Timezone Inspection (Floating vs Fixed)
// READ-ONLY — no modifications, just inspects two existing tasks
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Prerequisite: Run 01b first (creates TZ-PROBE-Floating and TZ-PROBE-Fixed)
// Intent: Run AFTER changing system timezone to compare how OmniJS
//         reports the same dueDate on a floating vs fixed task.
//
// Process:
//   1. Run 01b in home timezone (BST) — captures baseline
//   2. Switch system timezone (e.g., America/New_York)
//   3. Quit and reopen OmniFocus
//   4. Paste and run THIS script
//   5. Switch back to Europe/London, reopen OmniFocus

(() => {
  let r = `=== 01c: Cross-Timezone Inspection ===\n\n`;

  // --- Report current environment ---
  const now = new Date();
  r += `Current environment:\n`;
  r += `  now.toString():          ${now.toString()}\n`;
  r += `  now.getTimezoneOffset(): ${now.getTimezoneOffset()} min from UTC\n`;
  r += `  now.toISOString():       ${now.toISOString()}\n\n`;

  // --- Find both probe tasks ---
  let floating = null;
  let fixed = null;
  const tasks = flattenedTasks;
  for (let i = 0; i < tasks.length; i++) {
    const name = tasks[i].name;
    if (name === "TZ-PROBE-Floating") floating = tasks[i];
    if (name === "TZ-PROBE-Fixed") fixed = tasks[i];
  }

  if (!floating && !fixed) {
    return r + "ERROR: Neither TZ-PROBE-Floating nor TZ-PROBE-Fixed found. Run 01b first.\n";
  }

  // --- Helper ---
  function snapshot(label, task) {
    if (!task) {
      r += `  --- ${label} ---\n  NOT FOUND\n\n`;
      return null;
    }
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
    return dd ? dd.getTime() : null;
  }

  const floatingEpoch = snapshot("FLOATING TASK", floating);
  const fixedEpoch = snapshot("FIXED TASK", fixed);

  // --- Cross-task comparison ---
  r += `--- Floating vs Fixed (this timezone) ---\n\n`;
  if (floatingEpoch !== null && fixedEpoch !== null) {
    const delta = floatingEpoch - fixedEpoch;
    r += `  Floating getTime(): ${floatingEpoch}\n`;
    r += `  Fixed    getTime(): ${fixedEpoch}\n`;
    r += `  Delta:              ${delta} ms (${delta / 60000} min)\n\n`;

    if (delta === 0) {
      r += `  RESULT: Both tasks report the same UTC moment.\n`;
      r += `    The floating flag has no effect on the Date API in this timezone.\n`;
    } else {
      r += `  RESULT: Floating and Fixed report DIFFERENT UTC moments!\n`;
      r += `    Delta = ${delta / 60000} min — this is the floating reinterpretation.\n`;
    }
  }

  // --- Compare with BST baseline ---
  // (These are the values from running 01b in BST — both tasks were identical there)
  r += `\n--- Compare with BST baseline ---\n\n`;
  r += `  BST baseline (both tasks identical in home TZ):\n`;
  r += `    getTime():           1784109600000\n`;
  r += `    toISOString():       2026-07-15T10:00:00.000Z\n`;
  r += `    getTimezoneOffset(): -60 (BST)\n\n`;

  if (floatingEpoch !== null) {
    if (floatingEpoch === 1784109600000) {
      r += `  Floating task: UNCHANGED from BST baseline.\n`;
    } else {
      const deltaMin = (floatingEpoch - 1784109600000) / 60000;
      r += `  Floating task: CHANGED by ${deltaMin} min from BST baseline.\n`;
      r += `    Wall clock preserved → UTC moment shifted.\n`;
    }
  }

  if (fixedEpoch !== null) {
    if (fixedEpoch === 1784109600000) {
      r += `  Fixed task:    UNCHANGED from BST baseline.\n`;
      r += `    UTC moment preserved → wall clock shifted.\n`;
    } else {
      const deltaMin = (fixedEpoch - 1784109600000) / 60000;
      r += `  Fixed task:    CHANGED by ${deltaMin} min from BST baseline.\n`;
    }
  }

  r += `\n=== END ===\n`;
  return r;
})();
