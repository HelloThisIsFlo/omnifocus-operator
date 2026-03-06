// _common.js — Shared infrastructure for benchmark variants.
// Concatenated AFTER the variant file. The variant provides handleSnapshot().
// Function declarations are hoisted, so handleSnapshot() is available here.

var IPC_DIR_SUFFIX = "omnifocus-operator/ipc";

// --- Helper functions (from bridge.js) ---

function d(v) {
    return v ? v.toISOString() : null;
}

function pk(v) {
    return v ? v.id.primaryKey : null;
}

// --- Enum resolvers (from bridge.js) ---

function ts(s) {
    if (s === Task.Status.Available) return "Available";
    if (s === Task.Status.Blocked) return "Blocked";
    if (s === Task.Status.Completed) return "Completed";
    if (s === Task.Status.Dropped) return "Dropped";
    if (s === Task.Status.DueSoon) return "DueSoon";
    if (s === Task.Status.Next) return "Next";
    if (s === Task.Status.Overdue) return "Overdue";
    throw new Error("Unknown TaskStatus: " + String(s));
}

function ps(s) {
    if (s === Project.Status.Active) return "Active";
    if (s === Project.Status.OnHold) return "OnHold";
    if (s === Project.Status.Done) return "Done";
    if (s === Project.Status.Dropped) return "Dropped";
    throw new Error("Unknown ProjectStatus: " + String(s));
}

function gs(s) {
    if (s === Tag.Status.Active) return "Active";
    if (s === Tag.Status.OnHold) return "OnHold";
    if (s === Tag.Status.Dropped) return "Dropped";
    throw new Error("Unknown TagStatus: " + String(s));
}

function fs(s) {
    if (s === Folder.Status.Active) return "Active";
    if (s === Folder.Status.Dropped) return "Dropped";
    throw new Error("Unknown FolderStatus: " + String(s));
}

function rst(s) {
    if (s === Task.RepetitionScheduleType.Regularly) return "Regularly";
    if (s === Task.RepetitionScheduleType.FromCompletion) return "FromCompletion";
    if (s === Task.RepetitionScheduleType.None) return "None";
    throw new Error("Unknown RepetitionScheduleType: " + String(s));
}

function adk(s) {
    if (s === Task.AnchorDateKey.DueDate) return "DueDate";
    if (s === Task.AnchorDateKey.DeferDate) return "DeferDate";
    if (s === Task.AnchorDateKey.PlannedDate) return "PlannedDate";
    throw new Error("Unknown AnchorDateKey: " + String(s));
}

function rr(v) {
    if (!v) return null;
    return {
        ruleString: v.ruleString,
        scheduleType: rst(v.scheduleType),
        anchorDateKey: adk(v.anchorDateKey),
        catchUpAutomatically: v.catchUpAutomatically,
    };
}

function ri(v) {
    return v ? { steps: v.steps, unit: v.unit } : null;
}

// --- IPC functions (from bridge.js) ---

function readRequest(ipcDir, filePrefix) {
    var requestPath = ipcDir + "/" + filePrefix + ".request.json";
    var url = URL.fromPath(requestPath, false);
    var wrapper = FileWrapper.fromURL(url);
    return JSON.parse(wrapper.contents.toString());
}

function writeResponse(ipcDir, filePrefix, responseObj) {
    var filePath = ipcDir + "/" + filePrefix + ".response.json";
    var url = URL.fromPath(filePath, false);
    var data = Data.fromString(JSON.stringify(responseObj));
    var fw = FileWrapper.withContents(null, data);
    fw.write(url, [FileWrapper.WritingOptions.Atomic], null);
}

// --- Benchmark dispatch (modified from bridge.js) ---

function dispatch(ipcDir, filePrefix) {
    try {
        var request = readRequest(ipcDir, filePrefix);
        var start = Date.now();
        var data = handleSnapshot();
        data._benchmarkMs = Date.now() - start;
        writeResponse(ipcDir, filePrefix, { success: true, data: data });
    } catch (e) {
        writeResponse(ipcDir, filePrefix, { success: false, error: e.message });
        console.error("Benchmark error: " + e.message);
    }
}

// --- Entry point (production IIFE) ---

if (typeof module === "undefined") {
    (function () {
        var docsDir = URL.documentsDirectory.string.replace("file://", "");
        var ipcDir = docsDir + IPC_DIR_SUFFIX;
        dispatch(ipcDir, argument);
    })();
}
