(function () {
  var base =
    URL.documentsDirectory.string.replace("file://", "") +
    "omnifocus-operator/responses/";

  function write(id, obj) {
    var fw = FileWrapper.withContents(
      id + ".json",
      Data.fromString(JSON.stringify(obj)),
    );
    fw.write(
      URL.fromPath(base + id + ".json", false),
      [FileWrapper.WritingOptions.Atomic],
      null,
    );
  }

  function d(v) {
    return v ? v.toISOString() : null;
  }
  function pk(v) {
    return v ? v.id.primaryKey : null;
  }
  function rr(v) {
    return v
      ? { ruleString: v.ruleString, scheduleType: v.scheduleType.name }
      : null;
  }
  function ri(v) {
    return v ? { steps: v.steps, unit: v.unit } : null;
  }
  function ts(s) {
    if (s === Task.Status.Available) return "Available";
    if (s === Task.Status.Blocked) return "Blocked";
    if (s === Task.Status.Completed) return "Completed";
    if (s === Task.Status.Dropped) return "Dropped";
    if (s === Task.Status.DueSoon) return "DueSoon";
    if (s === Task.Status.Next) return "Next";
    if (s === Task.Status.Overdue) return "Overdue";
    return null;
  }

  var parts = argument.split("::::");
  var id = parts[0];
  var op = parts[1];

  try {
    if (op === "dump") {
      write(id, {
      success: true,
      data: {
        tasks: flattenedTasks.map(function (t) {
          return {
            id: t.id.primaryKey,
            name: t.name,
            note: t.note,
            added: d(t.added),
            modified: d(t.modified),
            active: t.active,
            effectiveActive: t.effectiveActive,
            status: ts(t.taskStatus),
            completed: t.completed,
            completedByChildren: t.completedByChildren,
            flagged: t.flagged,
            effectiveFlagged: t.effectiveFlagged,
            sequential: t.sequential,
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
            shouldUseFloatingTimeZone: t.shouldUseFloatingTimeZone,
            repetitionRule: rr(t.repetitionRule),
            project: pk(t.containingProject),
            parent: pk(t.parent),
            assignedContainer: pk(t.assignedContainer),
            tags: t.tags.map(function (g) {
              return g.name;
            }),
          };
        }),

        projects: flattenedProjects.map(function (p) {
          return {
            id: p.id.primaryKey,
            name: p.name,
            note: p.note,
            status: p.status ? p.status.name : null,
            taskStatus: ts(p.taskStatus),
            completed: p.completed,
            completedByChildren: p.completedByChildren,
            completionDate: d(p.completionDate),
            effectiveCompletionDate: d(p.effectiveCompletionDate),
            flagged: p.flagged,
            effectiveFlagged: p.effectiveFlagged,
            sequential: p.sequential,
            containsSingletonActions: p.containsSingletonActions,
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
            shouldUseFloatingTimeZone: p.shouldUseFloatingTimeZone,
            repetitionRule: rr(p.repetitionRule),
            lastReviewDate: d(p.lastReviewDate),
            nextReviewDate: d(p.nextReviewDate),
            reviewInterval: ri(p.reviewInterval),
            nextTask: pk(p.nextTask),
            folder: pk(p.parentFolder),
            tags: p.tags.map(function (g) {
              return g.name;
            }),
          };
        }),

        tags: flattenedTags.map(function (g) {
          return {
            id: g.id.primaryKey,
            name: g.name,
            added: d(g.added),
            modified: d(g.modified),
            active: g.active,
            effectiveActive: g.effectiveActive,
            status: g.status ? g.status.name : null,
            allowsNextAction: g.allowsNextAction,
            parent: pk(g.parent),
          };
        }),

        folders: flattenedFolders.map(function (f) {
          return {
            id: f.id.primaryKey,
            name: f.name,
            added: d(f.added),
            modified: d(f.modified),
            active: f.active,
            effectiveActive: f.effectiveActive,
            status: f.status ? f.status.name : null,
            parent: pk(f.parent),
          };
        }),

        perspectives: Perspective.all.map(function (p) {
          return {
            id: p.identifier || null,
            name: p.name,
            builtin: !p.identifier,
          };
        }),
      },
    });
    } else {
      write(id, { success: false, error: "Unknown operation: " + op });
    }
  } catch (e) {
    write(id, { success: false, error: e.message });
  }
})(argument);
