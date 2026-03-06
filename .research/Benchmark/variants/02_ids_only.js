// 02_ids_only: Just primary keys — iteration cost
function handleSnapshot() {
    return {
        tasks: flattenedTasks.map(function (t) {
            return { id: t.id.primaryKey };
        }),
        projects: flattenedProjects.map(function (p) {
            return { id: p.id.primaryKey };
        }),
        tags: flattenedTags.map(function (g) {
            return { id: g.id.primaryKey };
        }),
        folders: flattenedFolders.map(function (f) {
            return { id: f.id.primaryKey };
        }),
        perspectives: Perspective.all.map(function (p) {
            return { id: p.id ? p.id.primaryKey : null };
        }),
    };
}
