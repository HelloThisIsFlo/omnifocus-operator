import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock OmniFocus globals before requiring bridge.js
var mockWrite = vi.fn();

var mockFromURL = vi.fn(function () {
  return {
    contents: {
      toString: function () {
        return '{"operation": "get_all", "params": {}}';
      },
    },
  };
});

vi.stubGlobal("FileWrapper", {
  withContents: vi.fn(function (name, data) {
    return { write: mockWrite };
  }),
  fromURL: mockFromURL,
  WritingOptions: { Atomic: "atomic" },
});

vi.stubGlobal("URL", {
  fromPath: vi.fn(function (path) {
    return "url:" + path;
  }),
});

vi.stubGlobal("Data", {
  fromString: vi.fn(function (s) {
    return "data:" + s;
  }),
});

// Minimal entity mocks (needed for module load)
vi.stubGlobal("flattenedTasks", []);
vi.stubGlobal("flattenedProjects", []);
vi.stubGlobal("flattenedTags", []);
vi.stubGlobal("flattenedFolders", []);
vi.stubGlobal("Perspective", { all: [] });
vi.stubGlobal("console", { ...console, error: vi.fn() });

vi.stubGlobal("Task", {
  Status: {
    Available: "Available",
    Blocked: "Blocked",
    Completed: "Completed",
    Dropped: "Dropped",
    DueSoon: "DueSoon",
    Next: "Next",
    Overdue: "Overdue",
  },
  RepetitionScheduleType: {
    Regularly: "RST_Regularly",
    FromCompletion: "RST_FromCompletion",
    None: "RST_None",
  },
  AnchorDateKey: {
    DueDate: "ADK_DueDate",
    DeferDate: "ADK_DeferDate",
    PlannedDate: "ADK_PlannedDate",
  },
  byIdentifier: vi.fn(),
});

vi.stubGlobal("Project", {
  Status: { Active: "PS_Active", OnHold: "PS_OnHold", Done: "PS_Done", Dropped: "PS_Dropped" },
  byIdentifier: vi.fn(),
});

vi.stubGlobal("Tag", {
  Status: { Active: "TS_Active", OnHold: "TS_OnHold", Dropped: "TS_Dropped" },
  byIdentifier: vi.fn(),
});

vi.stubGlobal("Folder", {
  Status: { Active: "FS_Active", Dropped: "FS_Dropped" },
});

vi.stubGlobal("inbox", {
  beginning: "inbox-beginning-location",
  ending: "inbox-ending-location",
});

vi.stubGlobal("moveTasks", vi.fn());

var bridge = require("../../src/omnifocus_operator/bridge/bridge.js");

describe("handleEditTask", function () {
  var mockTask;
  var originalTask;
  var originalProject;
  var originalTag;

  beforeEach(function () {
    originalTask = globalThis.Task;
    originalProject = globalThis.Project;
    originalTag = globalThis.Tag;
    vi.clearAllMocks();

    mockTask = {
      id: { primaryKey: "task-edit-001" },
      name: "Original Name",
      note: "Original note",
      flagged: false,
      estimatedMinutes: null,
      dueDate: null,
      deferDate: null,
      plannedDate: null,
      clearTags: vi.fn(),
      addTags: vi.fn(),
      removeTags: vi.fn(),
    };

    // Restore Task with byIdentifier that returns our mock
    globalThis.Task = {
      Status: originalTask.Status,
      RepetitionScheduleType: originalTask.RepetitionScheduleType,
      AnchorDateKey: originalTask.AnchorDateKey,
      byIdentifier: vi.fn(function (id) {
        if (id === "task-edit-001") return mockTask;
        return null;
      }),
    };

    globalThis.Project = {
      Status: originalProject.Status,
      byIdentifier: vi.fn(function () {
        return null;
      }),
    };

    globalThis.Tag = {
      Status: originalTag.Status,
      byIdentifier: vi.fn(function () {
        return null;
      }),
    };
  });

  afterEach(function () {
    globalThis.Task = originalTask;
    globalThis.Project = originalProject;
    globalThis.Tag = originalTag;
  });

  // --- Task lookup ---

  it("throws when task not found", function () {
    expect(function () {
      bridge.handleEditTask({ id: "nonexistent" });
    }).toThrow("Task not found: nonexistent");
  });

  it("returns id and name after editing", function () {
    var result = bridge.handleEditTask({ id: "task-edit-001" });
    expect(result).toEqual({ id: "task-edit-001", name: "Original Name" });
  });

  // --- Field updates with hasOwnProperty ---

  it("updates name when provided", function () {
    bridge.handleEditTask({ id: "task-edit-001", name: "New Name" });
    expect(mockTask.name).toBe("New Name");
  });

  it("returns updated name in result", function () {
    var result = bridge.handleEditTask({ id: "task-edit-001", name: "Updated" });
    expect(result.name).toBe("Updated");
  });

  it("does not change name when omitted", function () {
    bridge.handleEditTask({ id: "task-edit-001" });
    expect(mockTask.name).toBe("Original Name");
  });

  it("updates note (including to null for clearing)", function () {
    bridge.handleEditTask({ id: "task-edit-001", note: null });
    expect(mockTask.note).toBeNull();
  });

  it("updates note to a string value", function () {
    bridge.handleEditTask({ id: "task-edit-001", note: "New note" });
    expect(mockTask.note).toBe("New note");
  });

  it("sets flagged to false using hasOwnProperty (falsy-safe)", function () {
    mockTask.flagged = true;
    bridge.handleEditTask({ id: "task-edit-001", flagged: false });
    expect(mockTask.flagged).toBe(false);
  });

  it("sets estimatedMinutes to 0 using hasOwnProperty (falsy-safe)", function () {
    mockTask.estimatedMinutes = 30;
    bridge.handleEditTask({ id: "task-edit-001", estimatedMinutes: 0 });
    expect(mockTask.estimatedMinutes).toBe(0);
  });

  it("clears estimatedMinutes when set to null", function () {
    mockTask.estimatedMinutes = 30;
    bridge.handleEditTask({ id: "task-edit-001", estimatedMinutes: null });
    expect(mockTask.estimatedMinutes).toBeNull();
  });

  it("sets dueDate from ISO string", function () {
    bridge.handleEditTask({ id: "task-edit-001", dueDate: "2026-06-15T10:00:00Z" });
    expect(mockTask.dueDate).toEqual(new Date("2026-06-15T10:00:00Z"));
  });

  it("clears dueDate when set to null", function () {
    mockTask.dueDate = new Date("2026-01-01T00:00:00Z");
    bridge.handleEditTask({ id: "task-edit-001", dueDate: null });
    expect(mockTask.dueDate).toBeNull();
  });

  it("sets deferDate from ISO string", function () {
    bridge.handleEditTask({ id: "task-edit-001", deferDate: "2026-06-10T08:00:00Z" });
    expect(mockTask.deferDate).toEqual(new Date("2026-06-10T08:00:00Z"));
  });

  it("clears deferDate when set to null", function () {
    bridge.handleEditTask({ id: "task-edit-001", deferDate: null });
    expect(mockTask.deferDate).toBeNull();
  });

  it("sets plannedDate from ISO string", function () {
    bridge.handleEditTask({ id: "task-edit-001", plannedDate: "2026-06-12T09:00:00Z" });
    expect(mockTask.plannedDate).toEqual(new Date("2026-06-12T09:00:00Z"));
  });

  it("clears plannedDate when set to null", function () {
    bridge.handleEditTask({ id: "task-edit-001", plannedDate: null });
    expect(mockTask.plannedDate).toBeNull();
  });

  // --- Tag management ---

  it("replaces all tags (replace mode)", function () {
    var tag1 = { id: { primaryKey: "tag-a" }, name: "urgent" };
    var tag2 = { id: { primaryKey: "tag-b" }, name: "work" };
    Tag.byIdentifier.mockImplementation(function (id) {
      if (id === "tag-a") return tag1;
      if (id === "tag-b") return tag2;
      return null;
    });

    bridge.handleEditTask({
      id: "task-edit-001",
      tagMode: "replace",
      tagIds: ["tag-a", "tag-b"],
    });

    expect(mockTask.clearTags).toHaveBeenCalled();
    expect(mockTask.addTags).toHaveBeenCalledWith([tag1, tag2]);
  });

  it("clears all tags when replace mode with empty tagIds", function () {
    bridge.handleEditTask({
      id: "task-edit-001",
      tagMode: "replace",
      tagIds: [],
    });

    expect(mockTask.clearTags).toHaveBeenCalled();
    expect(mockTask.addTags).not.toHaveBeenCalled();
  });

  it("adds tags (add mode)", function () {
    var tag1 = { id: { primaryKey: "tag-a" }, name: "urgent" };
    Tag.byIdentifier.mockReturnValueOnce(tag1);

    bridge.handleEditTask({
      id: "task-edit-001",
      tagMode: "add",
      tagIds: ["tag-a"],
    });

    expect(mockTask.clearTags).not.toHaveBeenCalled();
    expect(mockTask.addTags).toHaveBeenCalledWith([tag1]);
  });

  it("removes tags (remove mode)", function () {
    var tag1 = { id: { primaryKey: "tag-a" }, name: "urgent" };
    Tag.byIdentifier.mockReturnValueOnce(tag1);

    bridge.handleEditTask({
      id: "task-edit-001",
      tagMode: "remove",
      tagIds: ["tag-a"],
    });

    expect(mockTask.removeTags).toHaveBeenCalledWith([tag1]);
  });

  it("handles add_remove mode (removals first, then additions)", function () {
    var tagAdd = { id: { primaryKey: "tag-add" }, name: "new" };
    var tagRemove = { id: { primaryKey: "tag-rm" }, name: "old" };
    Tag.byIdentifier.mockImplementation(function (id) {
      if (id === "tag-add") return tagAdd;
      if (id === "tag-rm") return tagRemove;
      return null;
    });

    bridge.handleEditTask({
      id: "task-edit-001",
      tagMode: "add_remove",
      addTagIds: ["tag-add"],
      removeTagIds: ["tag-rm"],
    });

    // removeTags called before addTags
    expect(mockTask.removeTags).toHaveBeenCalledWith([tagRemove]);
    expect(mockTask.addTags).toHaveBeenCalledWith([tagAdd]);
    var removeOrder = mockTask.removeTags.mock.invocationCallOrder[0];
    var addOrder = mockTask.addTags.mock.invocationCallOrder[0];
    expect(removeOrder).toBeLessThan(addOrder);
  });

  it("throws on unknown tag ID in tag operations", function () {
    Tag.byIdentifier.mockReturnValue(null);

    expect(function () {
      bridge.handleEditTask({
        id: "task-edit-001",
        tagMode: "add",
        tagIds: ["nonexistent-tag"],
      });
    }).toThrow("Tag not found: nonexistent-tag");
  });

  // --- Movement ---

  it("moves to beginning of a project container", function () {
    var mockProject = {
      id: { primaryKey: "proj-001" },
      beginning: "proj-beginning-location",
    };
    Project.byIdentifier.mockReturnValueOnce(mockProject);

    bridge.handleEditTask({
      id: "task-edit-001",
      moveTo: { position: "beginning", containerId: "proj-001" },
    });

    expect(Project.byIdentifier).toHaveBeenCalledWith("proj-001");
    expect(moveTasks).toHaveBeenCalledWith([mockTask], "proj-beginning-location");
  });

  it("moves to ending of a project container", function () {
    var mockProject = {
      id: { primaryKey: "proj-002" },
      ending: "proj-ending-location",
    };
    Project.byIdentifier.mockReturnValueOnce(mockProject);

    bridge.handleEditTask({
      id: "task-edit-001",
      moveTo: { position: "ending", containerId: "proj-002" },
    });

    expect(moveTasks).toHaveBeenCalledWith([mockTask], "proj-ending-location");
  });

  it("moves to beginning of inbox when containerId is null", function () {
    bridge.handleEditTask({
      id: "task-edit-001",
      moveTo: { position: "beginning", containerId: null },
    });

    expect(moveTasks).toHaveBeenCalledWith([mockTask], "inbox-beginning-location");
  });

  it("moves to ending of inbox when containerId is null", function () {
    bridge.handleEditTask({
      id: "task-edit-001",
      moveTo: { position: "ending", containerId: null },
    });

    expect(moveTasks).toHaveBeenCalledWith([mockTask], "inbox-ending-location");
  });

  it("moves to before an anchor task", function () {
    var anchor = {
      id: { primaryKey: "anchor-task" },
      before: "before-anchor-location",
    };
    Task.byIdentifier.mockImplementation(function (id) {
      if (id === "task-edit-001") return mockTask;
      if (id === "anchor-task") return anchor;
      return null;
    });

    bridge.handleEditTask({
      id: "task-edit-001",
      moveTo: { position: "before", anchorId: "anchor-task" },
    });

    expect(moveTasks).toHaveBeenCalledWith([mockTask], "before-anchor-location");
  });

  it("moves to after an anchor task", function () {
    var anchor = {
      id: { primaryKey: "anchor-task" },
      after: "after-anchor-location",
    };
    Task.byIdentifier.mockImplementation(function (id) {
      if (id === "task-edit-001") return mockTask;
      if (id === "anchor-task") return anchor;
      return null;
    });

    bridge.handleEditTask({
      id: "task-edit-001",
      moveTo: { position: "after", anchorId: "anchor-task" },
    });

    expect(moveTasks).toHaveBeenCalledWith([mockTask], "after-anchor-location");
  });

  it("resolves container via Task.byIdentifier when Project returns null", function () {
    var parentTask = {
      id: { primaryKey: "parent-task" },
      ending: "parent-task-ending-location",
    };
    Project.byIdentifier.mockReturnValueOnce(null);
    Task.byIdentifier.mockImplementation(function (id) {
      if (id === "task-edit-001") return mockTask;
      if (id === "parent-task") return parentTask;
      return null;
    });

    bridge.handleEditTask({
      id: "task-edit-001",
      moveTo: { position: "ending", containerId: "parent-task" },
    });

    expect(moveTasks).toHaveBeenCalledWith([mockTask], "parent-task-ending-location");
  });

  it("throws on unknown container ID", function () {
    Project.byIdentifier.mockReturnValueOnce(null);
    Task.byIdentifier.mockImplementation(function (id) {
      if (id === "task-edit-001") return mockTask;
      return null;
    });

    expect(function () {
      bridge.handleEditTask({
        id: "task-edit-001",
        moveTo: { position: "beginning", containerId: "nonexistent" },
      });
    }).toThrow("Container not found: nonexistent");
  });

  it("throws on unknown anchor task ID", function () {
    Task.byIdentifier.mockImplementation(function (id) {
      if (id === "task-edit-001") return mockTask;
      return null;
    });

    expect(function () {
      bridge.handleEditTask({
        id: "task-edit-001",
        moveTo: { position: "before", anchorId: "nonexistent" },
      });
    }).toThrow("Anchor task not found: nonexistent");
  });

  // --- Combined operations ---

  it("applies field updates, tag changes, and movement in one call", function () {
    var tag1 = { id: { primaryKey: "tag-x" }, name: "x" };
    Tag.byIdentifier.mockReturnValueOnce(tag1);

    var mockProject = {
      id: { primaryKey: "proj-dest" },
      ending: "proj-dest-ending",
    };
    Project.byIdentifier.mockReturnValueOnce(mockProject);

    var result = bridge.handleEditTask({
      id: "task-edit-001",
      name: "Renamed",
      flagged: true,
      dueDate: "2026-12-31T23:59:59Z",
      tagMode: "replace",
      tagIds: ["tag-x"],
      moveTo: { position: "ending", containerId: "proj-dest" },
    });

    expect(mockTask.name).toBe("Renamed");
    expect(mockTask.flagged).toBe(true);
    expect(mockTask.dueDate).toEqual(new Date("2026-12-31T23:59:59Z"));
    expect(mockTask.clearTags).toHaveBeenCalled();
    expect(mockTask.addTags).toHaveBeenCalledWith([tag1]);
    expect(moveTasks).toHaveBeenCalledWith([mockTask], "proj-dest-ending");
    expect(result).toEqual({ id: "task-edit-001", name: "Renamed" });
  });
});
