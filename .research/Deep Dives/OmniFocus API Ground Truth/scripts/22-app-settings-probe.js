// 22 — Application & Settings Probe
// Runtime: Omni Automation (OmniFocus Automation Console)
// READ-ONLY
//
// Probes for accessible application and document settings.
// Key question: can we read the DueSoon threshold from the API?
// If so, the service layer can auto-detect it instead of requiring config.

(() => {
  let r = `=== 22: Application & Settings Probe ===\n\n`;

  // --- Application object ---
  r += `--- Application Object ---\n`;
  try { r += `  app.name: ${app.name}\n`; } catch(e) { r += `  app.name: error\n`; }
  try { r += `  app.version: ${app.version}\n`; } catch(e) { r += `  app.version: error\n`; }
  try { r += `  app.buildVersion: ${app.buildVersion}\n`; } catch(e) { r += `  app.buildVersion: error\n`; }
  try { r += `  app.platformName: ${app.platformName}\n`; } catch(e) { r += `  app.platformName: error\n`; }

  // --- App property probes ---
  r += `\n--- App Property Probes ---\n`;
  const appProbes = [
    "dueSoonInterval", "dueSoonThreshold", "dueSoonDays",
    "defaultDueSoonInterval", "preferences", "settings",
    "defaultTimezone", "timezone", "timeZone",
    "commandCenter", "toolbarStyle", "controlStyle"
  ];
  for (let i = 0; i < appProbes.length; i++) {
    try {
      const val = app[appProbes[i]];
      if (val !== undefined && val !== null) {
        r += `  ✅ app.${appProbes[i]}: ${typeof val === 'object' ? '[object ' + val.constructor.name + ']' : val}\n`;
      } else {
        r += `  ⚪ app.${appProbes[i]}: ${val}\n`;
      }
    } catch(e) {
      r += `  ❌ app.${appProbes[i]}: ${e.message}\n`;
    }
  }

  // --- Document object ---
  r += `\n--- Document Object ---\n`;
  try {
    const doc = document;
    r += `  document exists: yes\n`;

    const docProbes = [
      "name", "fileURL", "canRedo", "canUndo",
      "dueSoonInterval", "dueSoonThreshold", "dueSoonDays",
      "defaultDueSoonInterval", "settings", "preferences"
    ];
    for (let i = 0; i < docProbes.length; i++) {
      try {
        const val = doc[docProbes[i]];
        if (val !== undefined && val !== null) {
          r += `  ✅ doc.${docProbes[i]}: ${typeof val === 'object' ? '[object]' : val}\n`;
        } else {
          r += `  ⚪ doc.${docProbes[i]}: ${val}\n`;
        }
      } catch(e) {
        r += `  ❌ doc.${docProbes[i]}: ${e.message}\n`;
      }
    }
  } catch(e) {
    r += `  document: ${e.message}\n`;
  }

  // --- Settings object ---
  r += `\n--- Settings Object ---\n`;
  try {
    const s = Settings;
    r += `  Settings exists: ${s}\n`;
    const settingsProbes = [
      "dueSoon", "dueSoonInterval", "defaultDueDateStyle",
      "defaultDeferDateStyle", "compactLayout",
      "calendarBlockDuration", "reviewFrequency"
    ];
    for (let i = 0; i < settingsProbes.length; i++) {
      try {
        const val = s[settingsProbes[i]];
        r += `  Settings.${settingsProbes[i]}: ${val}\n`;
      } catch(e) {
        r += `  Settings.${settingsProbes[i]}: error\n`;
      }
    }
  } catch(e) {
    r += `  Settings: ${e.message}\n`;
  }

  // --- Preferences API ---
  r += `\n--- Preferences API ---\n`;
  try {
    const p = Preferences;
    r += `  Preferences exists: yes\n`;

    // Try reading known OmniFocus preference keys
    const prefKeys = [
      "DueSoonIntervalSetting", "DueSoonDays",
      "DefaultDueDateStyle", "DefaultDeferDateStyle",
      "QuickEntryEnabled", "ForecastShowDeferred",
      "CompletedTaskRetention", "ReviewInterval",
      "com.omnigroup.OmniFocus.DueSoonInterval",
      "DueSoonInterval", "dueSoonInterval"
    ];
    for (let i = 0; i < prefKeys.length; i++) {
      try {
        const val = p.read(prefKeys[i]);
        if (val !== undefined && val !== null) {
          r += `  ✅ Preferences.read("${prefKeys[i]}"): ${val}\n`;
        } else {
          r += `  ⚪ Preferences.read("${prefKeys[i]}"): ${val}\n`;
        }
      } catch(e) {
        r += `  ❌ Preferences.read("${prefKeys[i]}"): ${e.message}\n`;
      }
    }
  } catch(e) {
    r += `  Preferences: ${e.message}\n`;
  }

  // --- Alert/Notification intervals ---
  r += `\n--- Other Useful Probes ---\n`;
  try {
    r += `  Calendar.current: ${Calendar.current}\n`;
  } catch(e) {
    r += `  Calendar.current: error\n`;
  }
  try {
    r += `  TimeZone.abbreviations: ${JSON.stringify(TimeZone.abbreviations)}\n`;
  } catch(e) {
    r += `  TimeZone: error\n`;
  }

  return r;
})();
