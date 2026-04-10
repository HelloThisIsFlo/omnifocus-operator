// 01 — Timezone API Audit
// READ-ONLY — no modifications to OmniFocus data
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Answers: Q1 (timezone properties on Task), partially Q3 (hidden timezone columns)
//
// Sections:
//   A: shouldUseFloatingTimeZone distribution
//   B: Timezone property probe
//   C: Date object inspection
//   D: TimeZone + DateComponents probe
//   E: Database default (tasks without dates)

(() => {
  const tasks = flattenedTasks;
  const projects = flattenedProjects;
  const total = tasks.length;

  let r = `=== 01: Timezone API Audit ===\n`;
  r += `Total tasks: ${total}\n`;
  r += `Total projects: ${projects.length}\n\n`;

  // =========================================================================
  // A: shouldUseFloatingTimeZone distribution
  // =========================================================================
  r += `--- A: shouldUseFloatingTimeZone Distribution ---\n\n`;

  let taskFloating = { true: 0, false: 0, null: 0, other: 0 };
  let projFloating = { true: 0, false: 0, null: 0, other: 0 };

  for (let i = 0; i < total; i++) {
    const v = tasks[i].shouldUseFloatingTimeZone;
    if (v === true) taskFloating.true++;
    else if (v === false) taskFloating.false++;
    else if (v === null || v === undefined) taskFloating.null++;
    else taskFloating.other++;
  }

  for (let i = 0; i < projects.length; i++) {
    const t = projects[i].task;
    const v = t.shouldUseFloatingTimeZone;
    if (v === true) projFloating.true++;
    else if (v === false) projFloating.false++;
    else if (v === null || v === undefined) projFloating.null++;
    else projFloating.other++;
  }

  r += `  Tasks:\n`;
  r += `    true:  ${taskFloating.true}\n`;
  r += `    false: ${taskFloating.false}\n`;
  r += `    null:  ${taskFloating.null}\n`;
  r += `    other: ${taskFloating.other}\n`;
  r += `  Projects (via .task):\n`;
  r += `    true:  ${projFloating.true}\n`;
  r += `    false: ${projFloating.false}\n`;
  r += `    null:  ${projFloating.null}\n`;
  r += `    other: ${projFloating.other}\n\n`;

  // =========================================================================
  // B: Timezone property probe
  // =========================================================================
  r += `--- B: Timezone Property Probe ---\n\n`;

  // Pick a sample task with a dueDate
  let sampleTask = null;
  for (let i = 0; i < total; i++) {
    if (tasks[i].dueDate) {
      sampleTask = tasks[i];
      break;
    }
  }

  if (!sampleTask) {
    r += `  ERROR: No task with dueDate found!\n\n`;
  } else {
    r += `  Sample task: "${sampleTask.name}" (id: ${sampleTask.id.primaryKey})\n\n`;

    // Enumerate properties containing time/zone/tz/float/calendar
    const keywords = ["time", "zone", "tz", "float", "calendar"];
    let foundProps = [];

    // Get all enumerable properties
    let allProps = [];
    for (let key in sampleTask) {
      allProps.push(key);
    }
    // Also try Object.getOwnPropertyNames if available
    try {
      const ownProps = Object.getOwnPropertyNames(sampleTask);
      for (const p of ownProps) {
        if (allProps.indexOf(p) === -1) allProps.push(p);
      }
    } catch(e) {}

    for (const prop of allProps) {
      const lower = prop.toLowerCase();
      for (const kw of keywords) {
        if (lower.indexOf(kw) !== -1) {
          let val;
          try {
            val = sampleTask[prop];
            if (typeof val === "function") {
              val = "[function]";
            } else if (val instanceof Date) {
              val = `[Date] ${val.toISOString()}`;
            } else if (val !== null && typeof val === "object") {
              val = `[object] ${String(val)}`;
            }
          } catch(e) {
            val = `[ERROR] ${e.message}`;
          }
          foundProps.push({ name: prop, value: val, type: typeof sampleTask[prop] });
          break;
        }
      }
    }

    r += `  Properties matching time/zone/tz/float/calendar:\n`;
    if (foundProps.length === 0) {
      r += `    (none found in enumerable properties)\n`;
    } else {
      for (const p of foundProps) {
        r += `    ${p.name}: [${p.type}] ${p.value}\n`;
      }
    }

    // Specific property probes
    r += `\n  Specific property probes:\n`;
    const probes = ["timeZone", "calendar", "timezone", "floatingTimeZone",
                    "shouldUseFloatingTimeZone", "taskTimeZone"];
    for (const prop of probes) {
      try {
        const val = sampleTask[prop];
        if (val === undefined) {
          r += `    task.${prop}: undefined\n`;
        } else if (val === null) {
          r += `    task.${prop}: null\n`;
        } else if (val instanceof Date) {
          r += `    task.${prop}: [Date] ${val.toISOString()}\n`;
        } else if (typeof val === "object") {
          r += `    task.${prop}: [${typeof val}] ${String(val)}\n`;
        } else {
          r += `    task.${prop}: [${typeof val}] ${val}\n`;
        }
      } catch(e) {
        r += `    task.${prop}: [ERROR] ${e.message}\n`;
      }
    }
    r += `\n`;
  }

  // =========================================================================
  // C: Date object inspection
  // =========================================================================
  r += `--- C: Date Object Inspection ---\n\n`;

  if (sampleTask) {
    const dd = sampleTask.dueDate;
    const edd = sampleTask.effectiveDueDate;

    r += `  Task: "${sampleTask.name}"\n\n`;

    if (dd) {
      r += `  dueDate:\n`;
      r += `    typeof:           ${typeof dd}\n`;
      r += `    instanceof Date:  ${dd instanceof Date}\n`;
      r += `    toISOString():    ${dd.toISOString()}\n`;
      r += `    getTime():        ${dd.getTime()} (epoch ms)\n`;
      r += `    getTimezoneOffset(): ${dd.getTimezoneOffset()} (minutes from UTC)\n`;
      r += `    toString():       ${dd.toString()}\n`;
      try {
        r += `    toLocaleString(): ${dd.toLocaleString()}\n`;
      } catch(e) {
        r += `    toLocaleString(): [ERROR] ${e.message}\n`;
      }
    } else {
      r += `  dueDate: null\n`;
    }

    r += `\n`;

    if (edd) {
      r += `  effectiveDueDate:\n`;
      r += `    typeof:           ${typeof edd}\n`;
      r += `    instanceof Date:  ${edd instanceof Date}\n`;
      r += `    toISOString():    ${edd.toISOString()}\n`;
      r += `    getTime():        ${edd.getTime()} (epoch ms)\n`;
      r += `    getTimezoneOffset(): ${edd.getTimezoneOffset()} (minutes from UTC)\n`;
    } else {
      r += `  effectiveDueDate: null\n`;
    }

    // Compare: are dueDate and effectiveDueDate the same moment?
    if (dd && edd) {
      r += `\n  dueDate vs effectiveDueDate:\n`;
      r += `    Same epoch ms: ${dd.getTime() === edd.getTime()}\n`;
      r += `    Delta ms:      ${edd.getTime() - dd.getTime()}\n`;
    }
    r += `\n`;
  }

  // =========================================================================
  // D: TimeZone + DateComponents probe
  // =========================================================================
  r += `--- D: TimeZone + DateComponents Probe ---\n\n`;

  // TimeZone.abbreviations
  try {
    const abbrs = TimeZone.abbreviations;
    if (abbrs && typeof abbrs === "object") {
      const keys = Object.keys(abbrs);
      r += `  TimeZone.abbreviations: ${keys.length} entries\n`;
      // Show first 10
      r += `    Sample: ${keys.slice(0, 10).join(", ")}\n`;
    } else {
      r += `  TimeZone.abbreviations: ${String(abbrs)}\n`;
    }
  } catch(e) {
    r += `  TimeZone.abbreviations: [ERROR] ${e.message}\n`;
  }

  // Construct TimeZone objects
  r += `\n  TimeZone construction:\n`;
  const tzNames = ["EST", "UTC", "PST", "BST", "GMT", "Europe/London"];
  for (const name of tzNames) {
    try {
      const tz = new TimeZone(name);
      r += `    new TimeZone("${name}"): abbreviation=${tz.abbreviation}, `;
      r += `secondsFromGMT=${tz.secondsFromGMT}, `;
      r += `daylightSavingTime=${tz.daylightSavingTime}\n`;
    } catch(e) {
      r += `    new TimeZone("${name}"): [ERROR] ${e.message}\n`;
    }
  }

  // DateComponents from sample task's dueDate
  if (sampleTask && sampleTask.dueDate) {
    r += `\n  DateComponents from sample dueDate:\n`;
    try {
      const cal = Calendar.current;
      const dc = cal.dateComponentsFromDate(sampleTask.dueDate);
      r += `    year:     ${dc.year}\n`;
      r += `    month:    ${dc.month}\n`;
      r += `    day:      ${dc.day}\n`;
      r += `    hour:     ${dc.hour}\n`;
      r += `    minute:   ${dc.minute}\n`;
      r += `    second:   ${dc.second}\n`;
      r += `    timeZone: ${dc.timeZone}\n`;
      if (dc.timeZone) {
        r += `    timeZone.abbreviation: ${dc.timeZone.abbreviation}\n`;
        r += `    timeZone.secondsFromGMT: ${dc.timeZone.secondsFromGMT}\n`;
      }
    } catch(e) {
      r += `    [ERROR] ${e.message}\n`;
    }
  }
  r += `\n`;

  // =========================================================================
  // E: Database default — floating TZ on tasks with vs without dates
  // =========================================================================
  r += `--- E: Floating TZ — Tasks With vs Without Dates ---\n\n`;

  let withDates = { true: 0, false: 0, total: 0 };
  let withoutDates = { true: 0, false: 0, total: 0 };

  for (let i = 0; i < total; i++) {
    const t = tasks[i];
    const hasDates = (t.dueDate !== null || t.deferDate !== null);
    const floating = t.shouldUseFloatingTimeZone;

    if (hasDates) {
      withDates.total++;
      if (floating) withDates.true++; else withDates.false++;
    } else {
      withoutDates.total++;
      if (floating) withoutDates.true++; else withoutDates.false++;
    }
  }

  r += `  Tasks WITH dates (due or defer):\n`;
  r += `    total:  ${withDates.total}\n`;
  r += `    floating=true:  ${withDates.true}\n`;
  r += `    floating=false: ${withDates.false}\n`;
  r += `  Tasks WITHOUT dates:\n`;
  r += `    total:  ${withoutDates.total}\n`;
  r += `    floating=true:  ${withoutDates.true}\n`;
  r += `    floating=false: ${withoutDates.false}\n\n`;

  // Show a few specific examples
  r += `  Examples — tasks without dates:\n`;
  let noDateSamples = 0;
  for (let i = 0; i < total && noDateSamples < 3; i++) {
    const t = tasks[i];
    if (t.dueDate === null && t.deferDate === null) {
      r += `    "${t.name}": floating=${t.shouldUseFloatingTimeZone}\n`;
      noDateSamples++;
    }
  }

  r += `\n  Examples — tasks with dates:\n`;
  let hasDateSamples = 0;
  for (let i = 0; i < total && hasDateSamples < 3; i++) {
    const t = tasks[i];
    if (t.dueDate !== null || t.deferDate !== null) {
      r += `    "${t.name}": floating=${t.shouldUseFloatingTimeZone}`;
      if (t.dueDate) r += `, dueDate=${t.dueDate.toISOString()}`;
      if (t.deferDate) r += `, deferDate=${t.deferDate.toISOString()}`;
      r += `\n`;
      hasDateSamples++;
    }
  }

  r += `\n=== END ===\n`;
  return r;
})();
