// 05_with_enums: + enum-resolved fields — enum comparison cost
function handleSnapshot() {
    return {
        tasks: flattenedTasks.map(function (t) {
            return {
                id: t.id.primaryKey,
                name: t.name,
                note: t.note,
                added: d(t.added),
                modified: d(t.modified),
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
                active: t.active,
                effectiveActive: t.effectiveActive,
                status: ts(t.taskStatus),
                completed: t.completed,
                completedByChildren: t.completedByChildren,
                flagged: t.flagged,
                effectiveFlagged: t.effectiveFlagged,
                sequential: t.sequential,
                repetitionRule: rr(t.repetitionRule),
            };
        }),
        projects: flattenedProjects.map(function (p) {
            return {
                id: p.id.primaryKey,
                name: p.name,
                note: p.note,
                added: d(p.task.added),
                modified: d(p.task.modified),
                dueDate: d(p.dueDate),
                deferDate: d(p.deferDate),
                effectiveDueDate: d(p.effectiveDueDate),
                effectiveDeferDate: d(p.effectiveDeferDate),
                completionDate: d(p.completionDate),
                effectiveCompletionDate: d(p.effectiveCompletionDate),
                plannedDate: d(p.plannedDate),
                effectivePlannedDate: d(p.effectivePlannedDate),
                dropDate: d(p.dropDate),
                effectiveDropDate: d(p.effectiveDropDate),
                status: ps(p.status),
                taskStatus: ts(p.task.taskStatus),
                active: p.task.active,
                effectiveActive: p.task.effectiveActive,
                completed: p.completed,
                completedByChildren: p.completedByChildren,
                flagged: p.flagged,
                effectiveFlagged: p.effectiveFlagged,
                sequential: p.sequential,
                repetitionRule: rr(p.repetitionRule),
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
                status: gs(g.status),
                allowsNextAction: g.allowsNextAction,
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
                status: fs(f.status),
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
