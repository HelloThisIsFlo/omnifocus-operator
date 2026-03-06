// 04_with_dates: + all date fields — Date.toISOString cost
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
            };
        }),
        tags: flattenedTags.map(function (g) {
            return {
                id: g.id.primaryKey,
                name: g.name,
                added: d(g.added),
                modified: d(g.modified),
            };
        }),
        folders: flattenedFolders.map(function (f) {
            return {
                id: f.id.primaryKey,
                name: f.name,
                added: d(f.added),
                modified: d(f.modified),
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
