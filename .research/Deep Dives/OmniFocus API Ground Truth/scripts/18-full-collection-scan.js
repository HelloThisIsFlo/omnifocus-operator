// 18 — Full Collection Scan
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Scans ALL tasks (not just first 500) for linkedFileURLs,
// notifications, and attachments. Reports any non-empty collections
// with samples.

(() => {
  let r = `=== 18: Full Collection Scan ===\n\n`;

  const tasks = flattenedTasks;
  r += `Total tasks: ${tasks.length}\n\n`;

  let linkedCount = 0;
  let notifCount = 0;
  let attachCount = 0;
  const linkedSamples = [];
  const notifSamples = [];
  const attachSamples = [];
  let errors = 0;

  for (let i = 0; i < tasks.length; i++) {
    const t = tasks[i];

    try {
      if (t.linkedFileURLs && t.linkedFileURLs.length > 0) {
        linkedCount++;
        if (linkedSamples.length < 5) {
          linkedSamples.push({
            name: t.name,
            count: t.linkedFileURLs.length,
            first: String(t.linkedFileURLs[0])
          });
        }
      }
    } catch(e) { errors++; }

    try {
      if (t.notifications && t.notifications.length > 0) {
        notifCount++;
        if (notifSamples.length < 5) {
          notifSamples.push({
            name: t.name,
            count: t.notifications.length
          });
        }
      }
    } catch(e) { errors++; }

    try {
      if (t.attachments && t.attachments.length > 0) {
        attachCount++;
        if (attachSamples.length < 5) {
          attachSamples.push({
            name: t.name,
            count: t.attachments.length
          });
        }
      }
    } catch(e) { errors++; }
  }

  r += `--- Results ---\n`;
  r += `linkedFileURLs non-empty: ${linkedCount}/${tasks.length}\n`;
  r += `notifications non-empty: ${notifCount}/${tasks.length}\n`;
  r += `attachments non-empty: ${attachCount}/${tasks.length}\n`;
  r += `Errors during scan: ${errors}\n`;

  if (linkedSamples.length > 0) {
    r += `\n--- linkedFileURLs Samples ---\n`;
    for (let i = 0; i < linkedSamples.length; i++) {
      const s = linkedSamples[i];
      r += `  "${s.name}": ${s.count} URLs (first: ${s.first})\n`;
    }
  }

  if (notifSamples.length > 0) {
    r += `\n--- Notifications Samples ---\n`;
    for (let i = 0; i < notifSamples.length; i++) {
      const s = notifSamples[i];
      r += `  "${s.name}": ${s.count} notifications\n`;
    }
  }

  if (attachSamples.length > 0) {
    r += `\n--- Attachments Samples ---\n`;
    for (let i = 0; i < attachSamples.length; i++) {
      const s = attachSamples[i];
      r += `  "${s.name}": ${s.count} attachments\n`;
    }
  }

  if (linkedCount === 0 && notifCount === 0 && attachCount === 0) {
    r += `\nAll three collections are empty across the entire database.\n`;
  }

  return r;
})();
