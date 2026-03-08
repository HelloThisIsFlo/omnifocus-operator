import { describe, it, expect, vi, beforeEach } from "vitest";

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
    expect(result.tasks[0]).not.toHaveProperty("completedByChildren");
    expect(result.tasks[0]).not.toHaveProperty("sequential");
    expect(result.tasks[0]).not.toHaveProperty("shouldUseFloatingTimeZone");

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
    expect(result.projects[0]).not.toHaveProperty("completedByChildren");
    expect(result.projects[0]).not.toHaveProperty("sequential");
    expect(result.projects[0]).not.toHaveProperty("containsSingletonActions");
    expect(result.projects[0]).not.toHaveProperty("shouldUseFloatingTimeZone");
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
});
