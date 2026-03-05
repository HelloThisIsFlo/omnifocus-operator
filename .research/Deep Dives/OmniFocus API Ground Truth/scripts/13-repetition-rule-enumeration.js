// 13 — RepetitionRule Full Enumeration
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Scans ALL tasks with repetitionRule to enumerate:
// - All distinct RepetitionScheduleType values (probes beyond the 2 known)
// - All RRULE FREQ patterns and unique ruleStrings
// - Samples per scheduleType

(() => {
  let r = `=== 13: RepetitionRule Full Enumeration ===\n\n`;

  // --- Probe for all possible RepetitionScheduleType constants ---
  r += `--- RepetitionScheduleType Constant Probe ---\n`;
  const probeNames = [
    "Regularly", "FromCompletion", "DeferAnother", "DueAnother",
    "Fixed", "DeferUntil", "DueDate", "None", "Daily", "Weekly",
    "Monthly", "Yearly", "EveryNDays", "EveryNWeeks", "EveryNMonths",
    "AfterCompletion", "RepeatEvery", "DeferAnotherFromCompletion",
    "DueAgainAfterCompletion"
  ];
  const knownTypes = [];
  for (let i = 0; i < probeNames.length; i++) {
    const name = probeNames[i];
    try {
      const val = Task.RepetitionScheduleType[name];
      if (val !== undefined && val !== null) {
        knownTypes.push({ name: name, val: val });
        r += `  ${name}: EXISTS\n`;
      } else {
        r += `  ${name}: undefined\n`;
      }
    } catch(e) {
      r += `  ${name}: error (${e.message})\n`;
    }
  }
  r += `\nTotal known constants: ${knownTypes.length}\n`;

  // --- Scan all tasks ---
  const tasks = flattenedTasks;
  let withRule = 0;
  const scheduleTypeCounts = {};
  const freqCounts = {};
  const ruleStringCounts = {};

  for (let i = 0; i < tasks.length; i++) {
    const t = tasks[i];
    if (!t.repetitionRule) continue;
    withRule++;

    const rule = t.repetitionRule;
    const rs = rule.ruleString;
    const st = rule.scheduleType;

    // Match scheduleType
    let matched = "UNKNOWN";
    for (let j = 0; j < knownTypes.length; j++) {
      if (st === knownTypes[j].val) {
        matched = knownTypes[j].name;
        break;
      }
    }
    scheduleTypeCounts[matched] = (scheduleTypeCounts[matched] || 0) + 1;

    // Extract FREQ
    let freq = "NO_FREQ";
    if (rs) {
      const m = rs.match(/FREQ=(\w+)/);
      if (m) freq = m[1];
    }
    freqCounts[freq] = (freqCounts[freq] || 0) + 1;

    // Track unique ruleStrings
    if (rs) {
      ruleStringCounts[rs] = (ruleStringCounts[rs] || 0) + 1;
    }
  }

  r += `\n--- Results ---\n`;
  r += `Total tasks with repetitionRule: ${withRule}\n`;

  r += `\n--- ScheduleType Distribution ---\n`;
  const stKeys = Object.keys(scheduleTypeCounts).sort();
  let stSum = 0;
  for (let i = 0; i < stKeys.length; i++) {
    r += `  ${stKeys[i]}: ${scheduleTypeCounts[stKeys[i]]}\n`;
    stSum += scheduleTypeCounts[stKeys[i]];
  }
  r += `  Sum: ${stSum}/${withRule}\n`;

  r += `\n--- FREQ Pattern Distribution ---\n`;
  const fpKeys = Object.keys(freqCounts).sort();
  for (let i = 0; i < fpKeys.length; i++) {
    r += `  ${fpKeys[i]}: ${freqCounts[fpKeys[i]]}\n`;
  }

  r += `\n--- Unique RRULE Strings (${Object.keys(ruleStringCounts).length} distinct) ---\n`;
  const rsKeys = Object.keys(ruleStringCounts).sort();
  for (let i = 0; i < rsKeys.length; i++) {
    r += `  "${rsKeys[i]}": ${ruleStringCounts[rsKeys[i]]} tasks\n`;
  }

  // --- Samples per scheduleType ---
  r += `\n--- Samples (up to 3 per scheduleType) ---\n`;
  const samples = {};
  for (let i = 0; i < tasks.length; i++) {
    const t = tasks[i];
    if (!t.repetitionRule) continue;
    let matched = "UNKNOWN";
    for (let j = 0; j < knownTypes.length; j++) {
      if (t.repetitionRule.scheduleType === knownTypes[j].val) {
        matched = knownTypes[j].name;
        break;
      }
    }
    if (!samples[matched]) samples[matched] = [];
    if (samples[matched].length < 3) {
      samples[matched].push({
        name: t.name,
        ruleString: t.repetitionRule.ruleString
      });
    }
  }
  const sampleKeys = Object.keys(samples);
  for (let i = 0; i < sampleKeys.length; i++) {
    const type = sampleKeys[i];
    r += `\n  ${type}:\n`;
    for (let j = 0; j < samples[type].length; j++) {
      r += `    "${samples[type][j].name}": ${samples[type][j].ruleString}\n`;
    }
  }

  return r;
})();
