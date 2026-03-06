// 23 — Estimated Minutes Distribution
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Distribution analysis of estimatedMinutes across all tasks.
// Min, max, mean, median, buckets, most common values.
// Useful for time-based filtering design.

(() => {
  let r = `=== 23: Estimated Minutes Distribution ===\n\n`;

  const tasks = flattenedTasks;
  let nullCount = 0;
  const values = [];

  for (let i = 0; i < tasks.length; i++) {
    const em = tasks[i].estimatedMinutes;
    if (em === null || em === undefined) {
      nullCount++;
    } else {
      values.push(em);
    }
  }

  r += `Total tasks: ${tasks.length}\n`;
  r += `With estimate: ${values.length} (${(values.length / tasks.length * 100).toFixed(1)}%)\n`;
  r += `Without estimate (null): ${nullCount} (${(nullCount / tasks.length * 100).toFixed(1)}%)\n\n`;

  if (values.length === 0) {
    return r + `No estimates to analyze.\n`;
  }

  values.sort(function(a, b) { return a - b; });

  const min = values[0];
  const max = values[values.length - 1];
  let sum = 0;
  for (let i = 0; i < values.length; i++) sum += values[i];
  const mean = sum / values.length;
  const median = values.length % 2 === 0
    ? (values[Math.floor(values.length / 2) - 1] + values[Math.floor(values.length / 2)]) / 2
    : values[Math.floor(values.length / 2)];

  r += `--- Statistics ---\n`;
  r += `  Min: ${min} minutes\n`;
  r += `  Max: ${max} minutes\n`;
  r += `  Mean: ${mean.toFixed(1)} minutes\n`;
  r += `  Median: ${median} minutes\n`;
  r += `  Total time: ${(sum / 60).toFixed(1)} hours\n\n`;

  // Buckets
  const bucketDefs = [
    { label: "1-5 min", lo: 1, hi: 5 },
    { label: "6-15 min", lo: 6, hi: 15 },
    { label: "16-30 min", lo: 16, hi: 30 },
    { label: "31-60 min", lo: 31, hi: 60 },
    { label: "61-120 min", lo: 61, hi: 120 },
    { label: "121-240 min", lo: 121, hi: 240 },
    { label: "241+ min", lo: 241, hi: Infinity }
  ];

  r += `--- Distribution Buckets ---\n`;
  for (let b = 0; b < bucketDefs.length; b++) {
    let count = 0;
    for (let i = 0; i < values.length; i++) {
      if (values[i] >= bucketDefs[b].lo && values[i] <= bucketDefs[b].hi) count++;
    }
    r += `  ${bucketDefs[b].label}: ${count}\n`;
  }

  // Zero check
  let zeroCount = 0;
  for (let i = 0; i < values.length; i++) {
    if (values[i] === 0) zeroCount++;
  }
  r += `  Zero (0 min): ${zeroCount}\n`;

  // Most common values
  r += `\n--- Top 10 Most Common Values ---\n`;
  const valueCounts = {};
  for (let i = 0; i < values.length; i++) {
    valueCounts[values[i]] = (valueCounts[values[i]] || 0) + 1;
  }
  const sorted = [];
  const vcKeys = Object.keys(valueCounts);
  for (let i = 0; i < vcKeys.length; i++) {
    sorted.push({ value: Number(vcKeys[i]), count: valueCounts[vcKeys[i]] });
  }
  sorted.sort(function(a, b) { return b.count - a.count; });

  const showTop = Math.min(sorted.length, 10);
  for (let i = 0; i < showTop; i++) {
    r += `  ${sorted[i].value} min: ${sorted[i].count} tasks\n`;
  }

  // Distinct values count
  r += `\n--- Unique Values ---\n`;
  r += `  Distinct estimate values: ${vcKeys.length}\n`;

  return r;
})();
