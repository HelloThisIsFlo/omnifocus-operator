// OmniFocus Operator Bridge Script
// Runs inside OmniFocus's Omni Automation (JavaScriptCore) runtime.
// IPC dir is derived from URL.documentsDirectory at runtime (sandbox-safe).
//
// Protocol:
//   Request:  {IPC_DIR}/{argument}.request.json  -> {"operation": "get_all", "params": {}}
//   Response: {IPC_DIR}/{argument}.response.json  -> {"success": true, "data": {...}}
//
// Uses only OmniFocus globals: FileWrapper, URL, Data, flattenedTasks, etc.
// No require(), import/export, fs, path, or process.

// IPC_DIR is computed at runtime in the production IIFE below.
// In test mode, functions receive ipcDir as a parameter.
var IPC_DIR_SUFFIX = "omnifocus-operator/ipc";

// --- Helper functions ---

function d(v) {
    return v ? v.toISOString() : null;
}

function pk(v) {
    return v ? v.id.primaryKey : null;
}

// --- Enum resolvers ---
// OmniFocus enums are opaque objects. .name returns undefined.
// Only === comparison against known constants works.
// All resolvers throw on unknown values (fail-fast at bridge boundary).

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

// --- IPC functions ---

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

// --- Operation handlers ---

function handleGetAll() {
    return {
        tasks: flattenedTasks.map(function (t) {
            return {
                id: t.id.primaryKey,
                name: t.name,
                url: t.url.toString(),
                note: t.note,
                added: d(t.added),
                modified: d(t.modified),
                status: ts(t.taskStatus),
                flagged: t.flagged,
                effectiveFlagged: t.effectiveFlagged,
                dueDate: d(t.dueDate),
                deferDate: d(t.deferDate),
                effectiveDueDate: d(t.effectiveDueDate),
                effectiveDeferDate: d(t.effectiveDeferDate),
                completionDate: d(t.completionDate),
                effectiveCompletionDate: d(t.effectiveCompletionDate),
                plannedDate: d(t.plannedDate),
                effectivePlannedDate: d(t.effectivePlannedDate),
                dropDate: d(t.dropDate),
                effectiveDropDate: d(t.effectiveDropDate),
                estimatedMinutes: t.estimatedMinutes,
                hasChildren: t.hasChildren,
                inInbox: t.inInbox,
                repetitionRule: rr(t.repetitionRule),
                project: pk(t.containingProject),
                parent: pk(t.parent),
                tags: t.tags.map(function (g) {
                    return { id: g.id.primaryKey, name: g.name };
                }),
            };
        }),

        projects: flattenedProjects.map(function (p) {
            return {
                id: p.id.primaryKey,
                name: p.name,
                url: p.url.toString(),
                note: p.note,
                status: ps(p.status),
                taskStatus: ts(p.task.taskStatus),
                added: d(p.task.added),
                modified: d(p.task.modified),
                completionDate: d(p.completionDate),
                effectiveCompletionDate: d(p.effectiveCompletionDate),
                flagged: p.flagged,
                effectiveFlagged: p.effectiveFlagged,
                dueDate: d(p.dueDate),
                deferDate: d(p.deferDate),
                effectiveDueDate: d(p.effectiveDueDate),
                effectiveDeferDate: d(p.effectiveDeferDate),
                plannedDate: d(p.plannedDate),
                effectivePlannedDate: d(p.effectivePlannedDate),
                dropDate: d(p.dropDate),
                effectiveDropDate: d(p.effectiveDropDate),
                estimatedMinutes: p.estimatedMinutes,
                hasChildren: p.hasChildren,
                repetitionRule: rr(p.repetitionRule),
                lastReviewDate: d(p.lastReviewDate),
                nextReviewDate: d(p.nextReviewDate),
                reviewInterval: ri(p.reviewInterval),
                nextTask: pk(p.nextTask),
                folder: pk(p.parentFolder),
                tags: p.tags.map(function (g) {
                    return { id: g.id.primaryKey, name: g.name };
                }),
            };
        }),

        tags: flattenedTags.map(function (g) {
            return {
                id: g.id.primaryKey,
                name: g.name,
                url: g.url.toString(),
                added: d(g.added),
                modified: d(g.modified),
                status: gs(g.status),
                childrenAreMutuallyExclusive: g.childrenAreMutuallyExclusive,
                parent: pk(g.parent),
            };
        }),

        folders: flattenedFolders.map(function (f) {
            return {
                id: f.id.primaryKey,
                name: f.name,
                url: f.url.toString(),
                added: d(f.added),
                modified: d(f.modified),
                status: fs(f.status),
                parent: pk(f.parent),
            };
        }),

        perspectives: Perspective.all.map(function (p) {
            return {
                id: p.id ? p.id.primaryKey : null,
                name: p.name,
            };
        }),
    };
}

function handleAddTask(params) {
    var task;
    if (params.parent) {
        var container = Project.byIdentifier(params.parent)
            || Task.byIdentifier(params.parent);
        if (!container) {
            throw new Error("Parent not found: " + params.parent);
        }
        task = new Task(params.name, container);
    } else {
        task = new Task(params.name);
    }

    // Set optional fields (hasOwnProperty for booleans/numbers that can be falsy)
    if (params.dueDate) task.dueDate = new Date(params.dueDate);
    if (params.deferDate) task.deferDate = new Date(params.deferDate);
    if (params.plannedDate) task.plannedDate = new Date(params.plannedDate);
    if (params.hasOwnProperty("flagged")) task.flagged = params.flagged;
    if (params.hasOwnProperty("estimatedMinutes"))
        task.estimatedMinutes = params.estimatedMinutes;
    if (params.hasOwnProperty("note")) task.note = params.note;

    // Tags -- resolved by ID (service already validated and resolved names to IDs)
    if (params.tagIds && params.tagIds.length > 0) {
        var tags = params.tagIds.map(function(id) {
            var tag = Tag.byIdentifier(id);
            if (!tag) throw new Error("Tag not found: " + id);
            return tag;
        });
        task.addTags(tags);
    }

    return { id: task.id.primaryKey, name: task.name };
}

function handleEditTask(params) {
    var task = Task.byIdentifier(params.id);
    if (!task) {
        throw new Error("Task not found: " + params.id);
    }

    // Field updates -- hasOwnProperty for falsy-safe checks
    if (params.hasOwnProperty("name")) task.name = params.name;
    if (params.hasOwnProperty("note")) task.note = params.note;
    if (params.hasOwnProperty("flagged")) task.flagged = params.flagged;
    if (params.hasOwnProperty("estimatedMinutes"))
        task.estimatedMinutes = params.estimatedMinutes;
    if (params.hasOwnProperty("dueDate"))
        task.dueDate = params.dueDate ? new Date(params.dueDate) : null;
    if (params.hasOwnProperty("deferDate"))
        task.deferDate = params.deferDate ? new Date(params.deferDate) : null;
    if (params.hasOwnProperty("plannedDate"))
        task.plannedDate = params.plannedDate
            ? new Date(params.plannedDate)
            : null;

    // Tag management
    if (params.hasOwnProperty("tagMode")) {
        if (params.tagMode === "replace") {
            task.clearTags();
            if (params.tagIds && params.tagIds.length > 0) {
                var replaceObjs = params.tagIds.map(function (id) {
                    var tag = Tag.byIdentifier(id);
                    if (!tag) throw new Error("Tag not found: " + id);
                    return tag;
                });
                task.addTags(replaceObjs);
            }
        } else if (params.tagMode === "add") {
            var addObjs = params.tagIds.map(function (id) {
                var tag = Tag.byIdentifier(id);
                if (!tag) throw new Error("Tag not found: " + id);
                return tag;
            });
            task.addTags(addObjs);
        } else if (params.tagMode === "remove") {
            var removeObjs = params.tagIds.map(function (id) {
                var tag = Tag.byIdentifier(id);
                if (!tag) throw new Error("Tag not found: " + id);
                return tag;
            });
            task.removeTags(removeObjs);
        } else if (params.tagMode === "add_remove") {
            // Process removals first, then additions
            if (params.removeTagIds && params.removeTagIds.length > 0) {
                var rmObjs = params.removeTagIds.map(function (id) {
                    var tag = Tag.byIdentifier(id);
                    if (!tag) throw new Error("Tag not found: " + id);
                    return tag;
                });
                task.removeTags(rmObjs);
            }
            if (params.addTagIds && params.addTagIds.length > 0) {
                var addObjs2 = params.addTagIds.map(function (id) {
                    var tag = Tag.byIdentifier(id);
                    if (!tag) throw new Error("Tag not found: " + id);
                    return tag;
                });
                task.addTags(addObjs2);
            }
        }
    }

    // Movement
    if (params.hasOwnProperty("moveTo")) {
        var mv = params.moveTo;
        var location;
        if (mv.position === "beginning" || mv.position === "ending") {
            if (mv.containerId === null) {
                location = inbox[mv.position];
            } else {
                var container =
                    Project.byIdentifier(mv.containerId) ||
                    Task.byIdentifier(mv.containerId);
                if (!container) {
                    throw new Error("Container not found: " + mv.containerId);
                }
                location = container[mv.position];
            }
        } else if (mv.position === "before" || mv.position === "after") {
            var anchor = Task.byIdentifier(mv.anchorId);
            if (!anchor) {
                throw new Error("Anchor task not found: " + mv.anchorId);
            }
            location = anchor[mv.position];
        }
        moveTasks([task], location);
    }

    return { id: task.id.primaryKey, name: task.name };
}

// --- Dispatch ---

function dispatch(ipcDir, filePrefix) {
    try {
        var request = readRequest(ipcDir, filePrefix);
        var operation = request.operation;

        if (operation === "get_all") {
            var data = handleGetAll();
            writeResponse(ipcDir, filePrefix, { success: true, data: data });
        } else if (operation === "add_task") {
            var result = handleAddTask(request.params);
            writeResponse(ipcDir, filePrefix, { success: true, data: result });
        } else if (operation === "edit_task") {
            var editResult = handleEditTask(request.params);
            writeResponse(ipcDir, filePrefix, {
                success: true,
                data: editResult,
            });
        } else {
            writeResponse(ipcDir, filePrefix, {
                success: false,
                error: "Unknown operation: " + operation,
            });
        }
    } catch (e) {
        writeResponse(ipcDir, filePrefix, {
            success: false,
            error: e.message,
        });
        console.error("Bridge error: " + e.message);
    }
}

// --- Entry points ---

// Production entry: IIFE that runs in OmniFocus.
// The full script is passed inline via the omnifocus:///omnijs-run URL scheme.
// `argument` is OmniFocus's special variable containing the decoded &arg= value.
// IPC dir is derived from URL.documentsDirectory so that FileWrapper.write() has
// sandbox permission to write response files.
if (typeof module === "undefined") {
    (function () {
        var docsDir = URL.documentsDirectory.string.replace("file://", "");
        var ipcDir = docsDir + IPC_DIR_SUFFIX;
        dispatch(ipcDir, argument);
    })();
}

// Test entry: export functions for Vitest
if (typeof module !== "undefined") {
    module.exports = {
        readRequest: readRequest,
        writeResponse: writeResponse,
        handleGetAll: handleGetAll,
        handleAddTask: handleAddTask,
        handleEditTask: handleEditTask,
        dispatch: dispatch,
        d: d,
        pk: pk,
        rr: rr,
        ri: ri,
        ts: ts,
        ps: ps,
        gs: gs,
        fs: fs,
        rst: rst,
        adk: adk,
    };
}
