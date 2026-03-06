// 06_tasks_only: Full task mapping, empty others — task vs entity breakdown
function handleSnapshot() {
    return {
        tasks: flattenedTasks.map(function (t) {
            return {
                id: t.id.primaryKey,
                name: t.name,
                url: t.url.toString(),
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
                tags: t.tags.map(function (g) {
                    return { id: g.id.primaryKey, name: g.name };
                }),
            };
        }),
        projects: [],
        tags: [],
        folders: [],
        perspectives: [],
    };
}
