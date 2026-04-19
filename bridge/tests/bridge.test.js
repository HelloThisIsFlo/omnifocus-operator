import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

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

// Mock OmniFocus entity globals
vi.stubGlobal("flattenedTasks", [
  {
    id: { primaryKey: "task-001" },
    name: "Test Task",
    url: {
      toString: function () {
        return "omnifocus:///task/task-001";
      },
    },
    note: "A note",
    added: new Date("2026-01-01T00:00:00Z"),
    modified: new Date("2026-01-02T00:00:00Z"),
    taskStatus: "Available",
    flagged: false,
    effectiveFlagged: false,
    dueDate: null,
    deferDate: null,
    effectiveDueDate: null,
    effectiveDeferDate: null,
    completionDate: null,
    effectiveCompletionDate: null,
    plannedDate: null,
    effectivePlannedDate: null,
    dropDate: null,
    effectiveDropDate: null,
    estimatedMinutes: null,
    hasChildren: false,
    // Phase 56-02 raw fields (task property surface).
    completedByChildren: true,
    sequential: false,
    attachments: [{ id: "att-1" }],
    inInbox: false,
    repetitionRule: null,
    containingProject: { id: { primaryKey: "proj-001" } },
    parent: null,
    tags: [{ id: { primaryKey: "tag-001" }, name: "tag1" }],
  },
]);

vi.stubGlobal("flattenedProjects", [
  {
    id: { primaryKey: "proj-001" },
    name: "Test Project",
    url: {
      toString: function () {
        return "omnifocus:///project/proj-001";
      },
    },
    note: "",
    status: "PS_Active",
    task: {
      taskStatus: "Available",
      added: new Date("2026-01-01T00:00:00Z"),
      modified: new Date("2026-01-02T00:00:00Z"),
    },
    completionDate: null,
    effectiveCompletionDate: null,
    flagged: false,
    effectiveFlagged: false,
    dueDate: null,
    deferDate: null,
    effectiveDueDate: null,
    effectiveDeferDate: null,
    plannedDate: null,
    effectivePlannedDate: null,
    dropDate: null,
    effectiveDropDate: null,
    estimatedMinutes: null,
    hasChildren: true,
    // Phase 56-02 raw fields (project property surface).
    completedByChildren: false,
    sequential: true,
    containsSingletonActions: true,  // HIER-05 precedence test case
    attachments: [],
    repetitionRule: null,
    lastReviewDate: null,
    nextReviewDate: null,
    reviewInterval: null,
    nextTask: null,
    parentFolder: null,
    tags: [],
  },
]);

vi.stubGlobal("flattenedTags", [
  {
    id: { primaryKey: "tag-001" },
    name: "tag1",
    url: {
      toString: function () {
        return "omnifocus:///tag/tag-001";
      },
    },
    added: new Date("2026-01-01T00:00:00Z"),
    modified: new Date("2026-01-02T00:00:00Z"),
    status: "TS_Active",
    childrenAreMutuallyExclusive: false,
    parent: null,
  },
]);

vi.stubGlobal("flattenedFolders", [
  {
    id: { primaryKey: "folder-001" },
    name: "Test Folder",
    url: {
      toString: function () {
        return "omnifocus:///folder/folder-001";
      },
    },
    added: new Date("2026-01-01T00:00:00Z"),
    modified: new Date("2026-01-02T00:00:00Z"),
    status: "FS_Active",
    parent: null,
  },
]);

vi.stubGlobal("Perspective", {
  all: [
    {
      id: { primaryKey: "perspective-001" },
      name: "Forecast",
    },
  ],
});

// Mock Task.Status + RepetitionScheduleType + AnchorDateKey
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
});

// Mock Project.Status
vi.stubGlobal("Project", {
  Status: {
    Active: "PS_Active",
    OnHold: "PS_OnHold",
    Done: "PS_Done",
    Dropped: "PS_Dropped",
  },
});

// Mock Tag.Status
vi.stubGlobal("Tag", {
  Status: {
    Active: "TS_Active",
    OnHold: "TS_OnHold",
    Dropped: "TS_Dropped",
  },
});

// Mock Folder.Status
vi.stubGlobal("Folder", {
  Status: {
    Active: "FS_Active",
    Dropped: "FS_Dropped",
  },
});

// Mock console.error
vi.stubGlobal("console", {
  ...console,
  error: vi.fn(),
});

// Import bridge module (test mode: module is defined, so exports are available)
var bridge = require("../../src/omnifocus_operator/bridge/bridge.js");

describe("OmniFocus bug guard — batch tag methods are broken", function () {
  // OmniFocus has a bug where the batch methods addTags([...]) and
  // removeTags([...]) sometimes fail silently. The same call may work
  // or not work — it's completely unreliable. We work around this by
  // calling addTag/removeTag one tag at a time.
  //
  // These tests scan bridge.js source to ensure nobody accidentally
  // reintroduces the flaky batch calls.

  var source = readFileSync(
    resolve(__dirname, "../../src/omnifocus_operator/bridge/bridge.js"),
    "utf-8"
  );

  it("never calls task.addTags() (batch) — use addTag() one at a time instead", function () {
    var matches = source.match(/\.addTags\s*\(/g);
    expect(matches).toBeNull();
  });

  it("never calls task.removeTags() (batch) — use removeTag() one at a time instead", function () {
    var matches = source.match(/\.removeTags\s*\(/g);
    expect(matches).toBeNull();
  });
});

describe("helper functions", function () {
  it("d() formats dates to ISO string", function () {
    var date = new Date("2026-01-15T10:30:00Z");
    expect(bridge.d(date)).toBe("2026-01-15T10:30:00.000Z");
  });

  it("d() returns null for falsy values", function () {
    expect(bridge.d(null)).toBeNull();
    expect(bridge.d(undefined)).toBeNull();
  });

  it("pk() extracts primaryKey from object", function () {
    var obj = { id: { primaryKey: "abc-123" } };
    expect(bridge.pk(obj)).toBe("abc-123");
  });

  it("pk() returns null for falsy values", function () {
    expect(bridge.pk(null)).toBeNull();
    expect(bridge.pk(undefined)).toBeNull();
  });

  it("rr() extracts all 4 repetition rule fields", function () {
    var rule = {
      ruleString: "FREQ=DAILY",
      scheduleType: "RST_Regularly",
      anchorDateKey: "ADK_DueDate",
      catchUpAutomatically: true,
    };
    expect(bridge.rr(rule)).toEqual({
      ruleString: "FREQ=DAILY",
      scheduleType: "Regularly",
      anchorDateKey: "DueDate",
      catchUpAutomatically: true,
    });
  });

  it("rr() returns null for falsy values", function () {
    expect(bridge.rr(null)).toBeNull();
  });

  it("ri() extracts review interval", function () {
    var interval = { steps: 7, unit: "days" };
    expect(bridge.ri(interval)).toEqual({ steps: 7, unit: "days" });
  });

  it("ri() returns null for falsy values", function () {
    expect(bridge.ri(null)).toBeNull();
  });

  it("ts() maps Task.Status values to strings", function () {
    expect(bridge.ts("Available")).toBe("Available");
    expect(bridge.ts("Blocked")).toBe("Blocked");
    expect(bridge.ts("Completed")).toBe("Completed");
    expect(bridge.ts("Dropped")).toBe("Dropped");
    expect(bridge.ts("DueSoon")).toBe("DueSoon");
    expect(bridge.ts("Next")).toBe("Next");
    expect(bridge.ts("Overdue")).toBe("Overdue");
  });

  it("ts() throws on unknown status", function () {
    expect(function () {
      bridge.ts("Unknown");
    }).toThrow("Unknown TaskStatus: Unknown");
  });
});

describe("per-entity status resolvers", function () {
  it("ps() returns correct strings for all Project.Status values", function () {
    expect(bridge.ps("PS_Active")).toBe("Active");
    expect(bridge.ps("PS_OnHold")).toBe("OnHold");
    expect(bridge.ps("PS_Done")).toBe("Done");
    expect(bridge.ps("PS_Dropped")).toBe("Dropped");
  });

  it("ps() throws on unknown value", function () {
    expect(function () {
      bridge.ps("Unknown");
    }).toThrow("Unknown ProjectStatus: Unknown");
  });

  it("gs() returns correct strings for all Tag.Status values", function () {
    expect(bridge.gs("TS_Active")).toBe("Active");
    expect(bridge.gs("TS_OnHold")).toBe("OnHold");
    expect(bridge.gs("TS_Dropped")).toBe("Dropped");
  });

  it("gs() throws on unknown value", function () {
    expect(function () {
      bridge.gs("Unknown");
    }).toThrow("Unknown TagStatus: Unknown");
  });

  it("fs() returns correct strings for both Folder.Status values", function () {
    expect(bridge.fs("FS_Active")).toBe("Active");
    expect(bridge.fs("FS_Dropped")).toBe("Dropped");
  });

  it("fs() throws on unknown value", function () {
    expect(function () {
      bridge.fs("Unknown");
    }).toThrow("Unknown FolderStatus: Unknown");
  });
});

describe("repetition resolvers", function () {
  it("rst() returns correct strings for all RepetitionScheduleType values", function () {
    expect(bridge.rst("RST_Regularly")).toBe("Regularly");
    expect(bridge.rst("RST_FromCompletion")).toBe("FromCompletion");
    expect(bridge.rst("RST_None")).toBe("None");
  });

  it("rst() throws on unknown value", function () {
    expect(function () {
      bridge.rst("Unknown");
    }).toThrow("Unknown RepetitionScheduleType: Unknown");
  });

  it("adk() returns correct strings for all AnchorDateKey values", function () {
    expect(bridge.adk("ADK_DueDate")).toBe("DueDate");
    expect(bridge.adk("ADK_DeferDate")).toBe("DeferDate");
    expect(bridge.adk("ADK_PlannedDate")).toBe("PlannedDate");
  });

  it("adk() throws on unknown value", function () {
    expect(function () {
      bridge.adk("Unknown");
    }).toThrow("Unknown AnchorDateKey: Unknown");
  });
});

describe("readRequest", function () {
  beforeEach(function () {
    vi.clearAllMocks();
  });

  it("reads and parses request JSON from IPC directory", function () {
    mockFromURL.mockReturnValueOnce({
      contents: {
        toString: function () {
          return '{"operation": "get_all", "params": {}}';
        },
      },
    });

    var result = bridge.readRequest("/tmp/ipc", "123_uuid");
    expect(URL.fromPath).toHaveBeenCalledWith(
      "/tmp/ipc/123_uuid.request.json",
      false,
    );
    expect(mockFromURL).toHaveBeenCalled();
    expect(result).toEqual({ operation: "get_all", params: {} });
  });
});

describe("writeResponse", function () {
  beforeEach(function () {
    vi.clearAllMocks();
  });

  it("writes response JSON atomically via FileWrapper", function () {
    var responseObj = { success: true, data: { tasks: [] } };
    bridge.writeResponse("/tmp/ipc", "123_uuid", responseObj);

    expect(Data.fromString).toHaveBeenCalledWith(JSON.stringify(responseObj));
    expect(FileWrapper.withContents).toHaveBeenCalledWith(
      null,
      "data:" + JSON.stringify(responseObj),
    );
    expect(URL.fromPath).toHaveBeenCalledWith(
      "/tmp/ipc/123_uuid.response.json",
      false,
    );
    expect(mockWrite).toHaveBeenCalledWith(
      "url:/tmp/ipc/123_uuid.response.json",
      ["atomic"],
      null,
    );
  });
});

describe("handleGetAll", function () {
  it("collects all 5 entity types and returns structured data", function () {
    var result = bridge.handleGetAll();

    // Tasks
    expect(result.tasks).toHaveLength(1);
    expect(result.tasks[0].id).toBe("task-001");
    expect(result.tasks[0].name).toBe("Test Task");
    expect(result.tasks[0].url).toBe("omnifocus:///task/task-001");
    expect(result.tasks[0].project).toBe("proj-001");
    expect(result.tasks[0].tags).toEqual([{ id: "tag-001", name: "tag1" }]);
    expect(result.tasks[0]).not.toHaveProperty("assignedContainer");
    expect(result.tasks[0]).not.toHaveProperty("active");
    expect(result.tasks[0]).not.toHaveProperty("effectiveActive");
    expect(result.tasks[0]).not.toHaveProperty("completed");
    expect(result.tasks[0]).not.toHaveProperty("shouldUseFloatingTimeZone");
    // Phase 56-02: these are now live raw fields emitted to Python.
    expect(result.tasks[0]).toHaveProperty("completedByChildren");
    expect(result.tasks[0]).toHaveProperty("sequential");
    expect(result.tasks[0]).toHaveProperty("hasAttachments");

    // Projects
    expect(result.projects).toHaveLength(1);
    expect(result.projects[0].id).toBe("proj-001");
    expect(result.projects[0].name).toBe("Test Project");
    expect(result.projects[0].url).toBe("omnifocus:///project/proj-001");
    expect(result.projects[0].status).toBe("Active");
    expect(result.projects[0].taskStatus).toBe("Available");
    expect(result.projects[0]).not.toHaveProperty("active");
    expect(result.projects[0]).not.toHaveProperty("effectiveActive");
    expect(result.projects[0]).not.toHaveProperty("completed");
    expect(result.projects[0]).not.toHaveProperty("shouldUseFloatingTimeZone");
    // Phase 56-02: these are now live raw fields emitted to Python.
    expect(result.projects[0]).toHaveProperty("completedByChildren");
    expect(result.projects[0]).toHaveProperty("sequential");
    expect(result.projects[0]).toHaveProperty("containsSingletonActions");
    expect(result.projects[0]).toHaveProperty("hasAttachments");
    expect(result.projects[0].added).toBe("2026-01-01T00:00:00.000Z");
    expect(result.projects[0].modified).toBe("2026-01-02T00:00:00.000Z");

    // Tags
    expect(result.tags).toHaveLength(1);
    expect(result.tags[0].id).toBe("tag-001");
    expect(result.tags[0].name).toBe("tag1");
    expect(result.tags[0].url).toBe("omnifocus:///tag/tag-001");
    expect(result.tags[0].status).toBe("Active");
    expect(result.tags[0]).not.toHaveProperty("active");
    expect(result.tags[0]).not.toHaveProperty("effectiveActive");
    expect(result.tags[0]).not.toHaveProperty("allowsNextAction");
    expect(result.tags[0].childrenAreMutuallyExclusive).toBe(false);

    // Folders
    expect(result.folders).toHaveLength(1);
    expect(result.folders[0].id).toBe("folder-001");
    expect(result.folders[0].name).toBe("Test Folder");
    expect(result.folders[0].url).toBe("omnifocus:///folder/folder-001");
    expect(result.folders[0].status).toBe("Active");
    expect(result.folders[0]).not.toHaveProperty("active");
    expect(result.folders[0]).not.toHaveProperty("effectiveActive");

    // Perspectives
    expect(result.perspectives).toHaveLength(1);
    expect(result.perspectives[0].id).toBe("perspective-001");
    expect(result.perspectives[0].name).toBe("Forecast");
    expect(result.perspectives[0]).not.toHaveProperty("builtin");
  });

  // Phase 56-02: property-surface raw-field emission contract.
  it("emits completedByChildren / sequential / hasAttachments on tasks", function () {
    var result = bridge.handleGetAll();
    expect(result.tasks[0].completedByChildren).toBe(true);
    expect(result.tasks[0].sequential).toBe(false);
    expect(result.tasks[0].hasAttachments).toBe(true); // 1 attachment stub
  });

  it("emits completedByChildren / sequential / containsSingletonActions / hasAttachments on projects", function () {
    var result = bridge.handleGetAll();
    expect(result.projects[0].completedByChildren).toBe(false);
    expect(result.projects[0].sequential).toBe(true);
    expect(result.projects[0].containsSingletonActions).toBe(true);
    expect(result.projects[0].hasAttachments).toBe(false); // empty attachments
  });
});

describe("handleAddTask", function () {
  var originalTask;
  var originalProject;
  var originalTag;
  var createdTasks;

  beforeEach(function () {
    createdTasks = [];
    originalTask = globalThis.Task;
    originalProject = globalThis.Project;
    originalTag = globalThis.Tag;

    // Task constructor mock: new Task(name) or new Task(name, container)
    var TaskConstructor = function (name, container) {
      var t = {
        id: { primaryKey: "new-task-001" },
        name: name,
        container: container || null,
        dueDate: null,
        deferDate: null,
        plannedDate: null,
        flagged: false,
        estimatedMinutes: null,
        note: null,
        addTag: vi.fn(),
      };
      createdTasks.push(t);
      return t;
    };
    TaskConstructor.Status = originalTask.Status;
    TaskConstructor.RepetitionScheduleType = originalTask.RepetitionScheduleType;
    TaskConstructor.AnchorDateKey = originalTask.AnchorDateKey;
    TaskConstructor.byIdentifier = vi.fn(function () {
      return null;
    });
    globalThis.Task = TaskConstructor;

    // Project mock with byIdentifier
    globalThis.Project = {
      Status: originalProject.Status,
      byIdentifier: vi.fn(function () {
        return null;
      }),
    };

    // Tag mock with byIdentifier
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

  it("creates task with just name and returns id and name", function () {
    var result = bridge.handleAddTask({ name: "Buy milk" });

    expect(result).toEqual({ id: "new-task-001", name: "Buy milk" });
    expect(createdTasks).toHaveLength(1);
    expect(createdTasks[0].container).toBeNull();
  });

  it("creates task under project when parent found via Project.byIdentifier", function () {
    var mockProject = { id: { primaryKey: "proj-abc" }, name: "My Project" };
    Project.byIdentifier.mockReturnValueOnce(mockProject);

    var result = bridge.handleAddTask({ name: "Sub task", parent: "proj-abc" });

    expect(Project.byIdentifier).toHaveBeenCalledWith("proj-abc");
    expect(result).toEqual({ id: "new-task-001", name: "Sub task" });
    expect(createdTasks[0].container).toBe(mockProject);
  });

  it("creates task under task when parent found via Task.byIdentifier fallback", function () {
    var mockParentTask = { id: { primaryKey: "task-parent" }, name: "Parent" };
    Project.byIdentifier.mockReturnValueOnce(null);
    Task.byIdentifier.mockReturnValueOnce(mockParentTask);

    var result = bridge.handleAddTask({ name: "Child task", parent: "task-parent" });

    expect(Project.byIdentifier).toHaveBeenCalledWith("task-parent");
    expect(Task.byIdentifier).toHaveBeenCalledWith("task-parent");
    expect(createdTasks[0].container).toBe(mockParentTask);
  });

  it("throws error when parent not found in projects or tasks", function () {
    Project.byIdentifier.mockReturnValueOnce(null);
    Task.byIdentifier.mockReturnValueOnce(null);

    expect(function () {
      bridge.handleAddTask({ name: "Orphan", parent: "nonexistent-id" });
    }).toThrow("Parent not found: nonexistent-id");
  });

  it("sets optional date fields via new Date()", function () {
    var result = bridge.handleAddTask({
      name: "Dated task",
      dueDate: "2026-06-15T10:00:00Z",
      deferDate: "2026-06-10T08:00:00Z",
      plannedDate: "2026-06-12T09:00:00Z",
    });

    var task = createdTasks[0];
    expect(task.dueDate).toEqual(new Date("2026-06-15T10:00:00Z"));
    expect(task.deferDate).toEqual(new Date("2026-06-10T08:00:00Z"));
    expect(task.plannedDate).toEqual(new Date("2026-06-12T09:00:00Z"));
  });

  it("sets flagged and estimatedMinutes using hasOwnProperty (falsy-safe)", function () {
    var result = bridge.handleAddTask({
      name: "Falsy fields",
      flagged: false,
      estimatedMinutes: 0,
    });

    var task = createdTasks[0];
    expect(task.flagged).toBe(false);
    expect(task.estimatedMinutes).toBe(0);
  });

  it("sets note field", function () {
    bridge.handleAddTask({ name: "Noted", note: "Some details" });
    expect(createdTasks[0].note).toBe("Some details");
  });

  it("resolves tags by ID via Tag.byIdentifier and calls addTag per tag", function () {
    var mockTag1 = { id: { primaryKey: "tag-a" }, name: "urgent" };
    var mockTag2 = { id: { primaryKey: "tag-b" }, name: "work" };
    Tag.byIdentifier
      .mockReturnValueOnce(mockTag1)
      .mockReturnValueOnce(mockTag2);

    bridge.handleAddTask({
      name: "Tagged task",
      tagIds: ["tag-a", "tag-b"],
    });

    expect(Tag.byIdentifier).toHaveBeenCalledWith("tag-a");
    expect(Tag.byIdentifier).toHaveBeenCalledWith("tag-b");
    expect(createdTasks[0].addTag).toHaveBeenCalledWith(mockTag1);
    expect(createdTasks[0].addTag).toHaveBeenCalledWith(mockTag2);
  });

  it("throws error when tag not found by ID", function () {
    Tag.byIdentifier.mockReturnValueOnce(null);

    expect(function () {
      bridge.handleAddTask({ name: "Bad tags", tagIds: ["missing-tag"] });
    }).toThrow("Tag not found: missing-tag");
  });
});

describe("dispatch", function () {
  beforeEach(function () {
    vi.clearAllMocks();
    // Default: readRequest returns get_all operation
    mockFromURL.mockReturnValue({
      contents: {
        toString: function () {
          return '{"operation": "get_all", "params": {}}';
        },
      },
    });
  });

  it("routes get_all operation to handleGetAll and writes success response", function () {
    bridge.dispatch("/tmp/ipc", "123_uuid");

    // Should have written a response via FileWrapper
    expect(FileWrapper.withContents).toHaveBeenCalled();
    // withContents is called with null (no filename) in the new pattern
    var call = FileWrapper.withContents.mock.calls.find(function (c) {
      return c[0] === null && typeof c[1] === "string" && c[1].startsWith("data:");
    });
    expect(call).toBeDefined();

    // Parse the written data to verify structure
    var writtenJson = call[1].replace("data:", "");
    var response = JSON.parse(writtenJson);
    expect(response.success).toBe(true);
    expect(response.data).toHaveProperty("tasks");
    expect(response.data).toHaveProperty("projects");
    expect(response.data).toHaveProperty("tags");
    expect(response.data).toHaveProperty("folders");
    expect(response.data).toHaveProperty("perspectives");
  });

  it("writes error response for unknown operation", function () {
    mockFromURL.mockReturnValueOnce({
      contents: {
        toString: function () {
          return '{"operation": "unknown_op", "params": {}}';
        },
      },
    });

    bridge.dispatch("/tmp/ipc", "123_uuid");

    var call = FileWrapper.withContents.mock.calls.find(function (c) {
      return c[0] === null && typeof c[1] === "string" && c[1].startsWith("data:");
    });
    expect(call).toBeDefined();

    var writtenJson = call[1].replace("data:", "");
    var response = JSON.parse(writtenJson);
    expect(response.success).toBe(false);
    expect(response.error).toBe("Unknown operation: unknown_op");
  });

  it("writes error response and logs on OmniFocus API exception", function () {
    mockFromURL.mockReturnValueOnce({
      contents: {
        toString: function () {
          return '{"operation": "get_all", "params": {}}';
        },
      },
    });

    // Temporarily make flattenedTasks throw
    var originalTasks = globalThis.flattenedTasks;
    Object.defineProperty(globalThis, "flattenedTasks", {
      get: function () {
        throw new Error("OmniFocus API unavailable");
      },
      configurable: true,
    });

    bridge.dispatch("/tmp/ipc", "123_uuid");

    // Restore
    Object.defineProperty(globalThis, "flattenedTasks", {
      value: originalTasks,
      writable: true,
      configurable: true,
    });

    var call = FileWrapper.withContents.mock.calls.find(function (c) {
      return c[0] === null && typeof c[1] === "string" && c[1].startsWith("data:");
    });
    expect(call).toBeDefined();

    var writtenJson = call[1].replace("data:", "");
    var response = JSON.parse(writtenJson);
    expect(response.success).toBe(false);
    expect(response.error).toBe("OmniFocus API unavailable");
    expect(console.error).toHaveBeenCalledWith(
      "Bridge error: OmniFocus API unavailable",
    );
  });

  it("routes add_task operation to handleAddTask and writes success response", function () {
    // Save and replace Task/Project/Tag with constructable mocks
    var origTask = globalThis.Task;
    var origProject = globalThis.Project;
    var origTag = globalThis.Tag;

    var TaskCtor = function (name) {
      return {
        id: { primaryKey: "dispatch-task-001" },
        name: name,
        addTag: vi.fn(),
      };
    };
    TaskCtor.Status = origTask.Status;
    TaskCtor.RepetitionScheduleType = origTask.RepetitionScheduleType;
    TaskCtor.AnchorDateKey = origTask.AnchorDateKey;
    TaskCtor.byIdentifier = vi.fn();
    globalThis.Task = TaskCtor;
    globalThis.Project = { Status: origProject.Status, byIdentifier: vi.fn() };
    globalThis.Tag = { Status: origTag.Status, byIdentifier: vi.fn() };

    mockFromURL.mockReturnValueOnce({
      contents: {
        toString: function () {
          return '{"operation": "add_task", "params": {"name": "Dispatch test"}}';
        },
      },
    });

    bridge.dispatch("/tmp/ipc", "456_uuid");

    var call = FileWrapper.withContents.mock.calls.find(function (c) {
      return c[0] === null && typeof c[1] === "string" && c[1].startsWith("data:");
    });
    expect(call).toBeDefined();

    var writtenJson = call[1].replace("data:", "");
    var response = JSON.parse(writtenJson);
    expect(response.success).toBe(true);
    expect(response.data).toEqual({ id: "dispatch-task-001", name: "Dispatch test" });

    // Restore
    globalThis.Task = origTask;
    globalThis.Project = origProject;
    globalThis.Tag = origTag;
  });
});

describe("handleGetSettings", function () {
  var originalSettings;

  beforeEach(function () {
    originalSettings = globalThis.settings;
  });

  afterEach(function () {
    globalThis.settings = originalSettings;
  });

  it("returns all 7 keys when settings stub provides values for each", function () {
    var stubValues = {
      DefaultDueTime: "17:00:00",
      DefaultStartTime: "00:00:00",
      DefaultPlannedTime: "09:00:00",
      DueSoonInterval: 172800,
      DueSoonGranularity: 1,
      OFMCompleteWhenLastItemComplete: true,
      OFMTaskDefaultSequential: false,
    };
    vi.stubGlobal("settings", {
      objectForKey: vi.fn(function (key) {
        return stubValues[key];
      }),
    });

    var result = bridge.handleGetSettings();

    expect(result).toEqual(stubValues);
    // All 7 keys must be present in the returned object.
    expect(Object.keys(result)).toHaveLength(7);
    expect(result).toHaveProperty("OFMCompleteWhenLastItemComplete", true);
    expect(result).toHaveProperty("OFMTaskDefaultSequential", false);
  });

  it("preserves null values for the two new keys when settings stub returns null (absence surfaced to Python)", function () {
    var stubValues = {
      DefaultDueTime: "17:00:00",
      DefaultStartTime: "00:00:00",
      DefaultPlannedTime: "09:00:00",
      DueSoonInterval: 172800,
      DueSoonGranularity: 1,
      OFMCompleteWhenLastItemComplete: null,
      OFMTaskDefaultSequential: null,
    };
    vi.stubGlobal("settings", {
      objectForKey: vi.fn(function (key) {
        return stubValues[key];
      }),
    });

    var result = bridge.handleGetSettings();

    expect(Object.keys(result)).toHaveLength(7);
    // Absence is preserved so Python-side can apply factory-default fallback.
    expect(result).toHaveProperty("OFMCompleteWhenLastItemComplete", null);
    expect(result).toHaveProperty("OFMTaskDefaultSequential", null);
  });
});
