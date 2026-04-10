// 05 — OmniFocus Settings API Discovery
// READ-ONLY — no mutations
// Runtime: Omni Automation (OmniFocus Automation Console)
//
// Lists all available settings keys and reads date/time-relevant values.

(() => {
  let r = `=== 05: OmniFocus Settings API ===\n\n`;

  // --- All keys (sorted) ---
  r += `--- All Settings Keys ---\n\n`;
  r += settings.keys.sort().join("\n");

  // --- Date/time-relevant values ---
  r += `\n\n--- Date/Time Settings (values) ---\n\n`;
  const dateKeys = [
    "DefaultDueTime",
    "DefaultStartTime",
    "DefaultPlannedTime",
    "DefaultFloatingTimeZone",
    "DefaultScheduledNotificationTime",
    "DueSoonGranularity",
    "DueSoonInterval",
  ];
  for (const key of dateKeys) {
    const val = settings.objectForKey(key);
    const def = settings.defaultObjectForKey(key);
    r += `  ${key}:\n`;
    r += `    value:   ${val}\n`;
    r += `    default: ${def}\n`;
  }

  r += `\n=== END ===\n`;
  return r;
})();
