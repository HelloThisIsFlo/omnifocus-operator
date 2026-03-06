// 09_no_relations: Realistic "derive what we can in Python" variant.
// Dropped: url (constructible from PK), tag name in task/project tag arrays.
// Kept: all relationship PKs (project, parent, folder, nextTask) — not derivable.
// Tags on tasks/projects: just PKs (Python joins with the tags array).
// Compare against 07_full to measure realistic savings.
function handleSnapshot() {
    return {
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
                tags: t.tags.map(function (g) {
                    return g.id.primaryKey;
                }),
            };
        }),

        projects: flattenedProjects.map(function (p) {
            return {
                id: p.id.primaryKey,
                name: p.name,
                note: p.note,
                status: ps(p.status),
                taskStatus: ts(p.task.taskStatus),
                active: p.task.active,
                effectiveActive: p.task.effectiveActive,
                added: d(p.task.added),
                modified: d(p.task.modified),
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
                    return g.id.primaryKey;
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
                status: gs(g.status),
                allowsNextAction: g.allowsNextAction,
                childrenAreMutuallyExclusive: g.childrenAreMutuallyExclusive,
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
