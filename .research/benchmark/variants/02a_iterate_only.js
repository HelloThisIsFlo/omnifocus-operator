// 02a_iterate_only: Map to empty string — pure iteration without any property access
function handleSnapshot() {
    return {
        tasks: flattenedTasks.map(function () { return ""; }),
        projects: flattenedProjects.map(function () { return ""; }),
        tags: flattenedTags.map(function () { return ""; }),
        folders: flattenedFolders.map(function () { return ""; }),
        perspectives: Perspective.all.map(function () { return ""; }),
    };
}
