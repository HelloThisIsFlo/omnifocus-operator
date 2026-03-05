// 13 — RepetitionRule Full Enumeration
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Scans ALL tasks with repetitionRule to enumerate:
// - All distinct RepetitionScheduleType values
// - All distinct AnchorDateKey values
// - catchUpAutomatically distribution
// - .name accessor test on opaque enums (scheduleType, anchorDateKey)
// - firstDateAfterDate method existence
// - All RRULE FREQ patterns and unique ruleStrings
// - Cross-tabulation: scheduleType x anchorDateKey
// - Samples per scheduleType

(() => {
  let r = `=== 13: RepetitionRule Full Enumeration ===\n\n`;

  // --- Probe RepetitionScheduleType constants ---
  r += `--- RepetitionScheduleType Constant Probe ---\n`;
  const stProbeNames = [
    "Regularly", "FromCompletion", "None",
    "DeferAnother", "DueAnother", "Fixed", "DeferUntil", "DueDate",
    "Daily", "Weekly", "Monthly", "Yearly",
    "EveryNDays", "EveryNWeeks", "EveryNMonths",
    "AfterCompletion", "RepeatEvery",
    "DeferAnotherFromCompletion", "DueAgainAfterCompletion"
  ];
  const knownTypes = [];
  for (let i = 0; i < stProbeNames.length; i++) {
    const name = stProbeNames[i];
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
  r += `Total known ScheduleType constants: ${knownTypes.length}\n`;

  // --- Probe AnchorDateKey constants ---
  r += `\n--- AnchorDateKey Constant Probe ---\n`;
  const akProbeNames = [
    "DueDate", "DeferDate", "PlannedDate",
    "CompletionDate", "DropDate", "StartDate", "EndDate", "None"
  ];
  const knownAnchors = [];
  for (let i = 0; i < akProbeNames.length; i++) {
    const name = akProbeNames[i];
    try {
      const val = Task.AnchorDateKey[name];
      if (val !== undefined && val !== null) {
        knownAnchors.push({ name: name, val: val });
        r += `  ${name}: EXISTS\n`;
      } else {
        r += `  ${name}: undefined\n`;
      }
    } catch(e) {
      r += `  ${name}: error (${e.message})\n`;
    }
  }
  r += `Total known AnchorDateKey constants: ${knownAnchors.length}\n`;

  // --- .name accessor test ---
  r += `\n--- .name Accessor Test (do opaque enums support .name?) ---\n`;
  for (let i = 0; i < knownTypes.length; i++) {
    try {
      const n = knownTypes[i].val.name;
      r += `  ScheduleType.${knownTypes[i].name}.name = ${JSON.stringify(n)}\n`;
    } catch(e) {
      r += `  ScheduleType.${knownTypes[i].name}.name = ERROR: ${e.message}\n`;
    }
  }
  for (let i = 0; i < knownAnchors.length; i++) {
    try {
      const n = knownAnchors[i].val.name;
      r += `  AnchorDateKey.${knownAnchors[i].name}.name = ${JSON.stringify(n)}\n`;
    } catch(e) {
      r += `  AnchorDateKey.${knownAnchors[i].name}.name = ERROR: ${e.message}\n`;
    }
  }

  // --- Scan all tasks ---
  const tasks = flattenedTasks;
  let withRule = 0;
  const scheduleTypeCounts = {};
  const anchorDateKeyCounts = {};
  const crossTab = {};
  const freqCounts = {};
  const ruleStringCounts = {};
  let catchUpTrue = 0;
  let catchUpFalse = 0;
  let catchUpOther = 0;
  let hasFirstDateAfterDate = 0;
  let noFirstDateAfterDate = 0;

  for (let i = 0; i < tasks.length; i++) {
    const t = tasks[i];
    if (!t.repetitionRule) continue;
    withRule++;

    const rule = t.repetitionRule;
    const rs = rule.ruleString;

    // Match scheduleType
    let stMatched = "UNKNOWN";
    for (let j = 0; j < knownTypes.length; j++) {
      if (rule.scheduleType === knownTypes[j].val) {
        stMatched = knownTypes[j].name;
        break;
      }
    }
    scheduleTypeCounts[stMatched] = (scheduleTypeCounts[stMatched] || 0) + 1;

    // Match anchorDateKey
    let akMatched = "UNKNOWN";
    if (rule.anchorDateKey === undefined || rule.anchorDateKey === null) {
      akMatched = "NULL/UNDEFINED";
    } else {
      for (let j = 0; j < knownAnchors.length; j++) {
        if (rule.anchorDateKey === knownAnchors[j].val) {
          akMatched = knownAnchors[j].name;
          break;
        }
      }
    }
    anchorDateKeyCounts[akMatched] = (anchorDateKeyCounts[akMatched] || 0) + 1;

    // Cross-tabulation: scheduleType x anchorDateKey
    const crossKey = stMatched + " x " + akMatched;
    crossTab[crossKey] = (crossTab[crossKey] || 0) + 1;

    // catchUpAutomatically
    if (rule.catchUpAutomatically === true) catchUpTrue++;
    else if (rule.catchUpAutomatically === false) catchUpFalse++;
    else catchUpOther++;

    // firstDateAfterDate existence (check once per rule)
    if (typeof rule.firstDateAfterDate === "function") hasFirstDateAfterDate++;
    else noFirstDateAfterDate++;

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

  r += `\n--- AnchorDateKey Distribution ---\n`;
  const akKeys = Object.keys(anchorDateKeyCounts).sort();
  let akSum = 0;
  for (let i = 0; i < akKeys.length; i++) {
    r += `  ${akKeys[i]}: ${anchorDateKeyCounts[akKeys[i]]}\n`;
    akSum += anchorDateKeyCounts[akKeys[i]];
  }
  r += `  Sum: ${akSum}/${withRule}\n`;

  r += `\n--- ScheduleType x AnchorDateKey Cross-Tabulation ---\n`;
  const ctKeys = Object.keys(crossTab).sort();
  for (let i = 0; i < ctKeys.length; i++) {
    r += `  ${ctKeys[i]}: ${crossTab[ctKeys[i]]}\n`;
  }

  r += `\n--- catchUpAutomatically Distribution ---\n`;
  r += `  true: ${catchUpTrue}\n`;
  r += `  false: ${catchUpFalse}\n`;
  r += `  other (null/undefined): ${catchUpOther}\n`;

  r += `\n--- firstDateAfterDate Method ---\n`;
  r += `  exists (function): ${hasFirstDateAfterDate}\n`;
  r += `  missing: ${noFirstDateAfterDate}\n`;

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

  // --- Samples per scheduleType (now includes anchorDateKey + catchUp) ---
  r += `\n--- Samples (up to 3 per scheduleType) ---\n`;
  const samples = {};
  for (let i = 0; i < tasks.length; i++) {
    const t = tasks[i];
    if (!t.repetitionRule) continue;
    let stMatched = "UNKNOWN";
    for (let j = 0; j < knownTypes.length; j++) {
      if (t.repetitionRule.scheduleType === knownTypes[j].val) {
        stMatched = knownTypes[j].name;
        break;
      }
    }
    let akMatched = "UNKNOWN";
    if (t.repetitionRule.anchorDateKey !== undefined && t.repetitionRule.anchorDateKey !== null) {
      for (let j = 0; j < knownAnchors.length; j++) {
        if (t.repetitionRule.anchorDateKey === knownAnchors[j].val) {
          akMatched = knownAnchors[j].name;
          break;
        }
      }
    }
    if (!samples[stMatched]) samples[stMatched] = [];
    if (samples[stMatched].length < 3) {
      samples[stMatched].push({
        name: t.name,
        ruleString: t.repetitionRule.ruleString,
        anchorDateKey: akMatched,
        catchUp: t.repetitionRule.catchUpAutomatically
      });
    }
  }
  const sampleKeys = Object.keys(samples);
  for (let i = 0; i < sampleKeys.length; i++) {
    const type = sampleKeys[i];
    r += `\n  ${type}:\n`;
    for (let j = 0; j < samples[type].length; j++) {
      const s = samples[type][j];
      r += `    "${s.name}": ${s.ruleString} | anchor=${s.anchorDateKey} | catchUp=${s.catchUp}\n`;
    }
  }

  return r;
})();
