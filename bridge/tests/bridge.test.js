import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock OmniFocus globals before requiring bridge.js
var mockWrite = vi.fn();

var mockFromURL = vi.fn(function () {
  return {
    contents: {
      toString: function () {
        return '{"operation": "snapshot", "params": {}}';
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
    note: "A note",
    added: new Date("2026-01-01T00:00:00Z"),
    modified: new Date("2026-01-02T00:00:00Z"),
    active: true,
    effectiveActive: true,
    taskStatus: "Available",
    completed: false,
    completedByChildren: false,
    flagged: false,
    effectiveFlagged: false,
    sequential: false,
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
    shouldUseFloatingTimeZone: false,
    repetitionRule: null,
    containingProject: { id: { primaryKey: "proj-001" } },
    parent: null,
    assignedContainer: null,
    tags: [{ name: "tag1" }],
  },
]);

vi.stubGlobal("flattenedProjects", [
  {
    id: { primaryKey: "proj-001" },
    name: "Test Project",
    note: "",
    status: { name: "Active" },
    taskStatus: "Available",
    completed: false,
    completedByChildren: false,
    completionDate: null,
    effectiveCompletionDate: null,
    flagged: false,
    effectiveFlagged: false,
    sequential: false,
    containsSingletonActions: false,
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
    shouldUseFloatingTimeZone: false,
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
    added: new Date("2026-01-01T00:00:00Z"),
    modified: new Date("2026-01-02T00:00:00Z"),
    active: true,
    effectiveActive: true,
    status: { name: "Active" },
    allowsNextAction: true,
    parent: null,
  },
]);

vi.stubGlobal("flattenedFolders", [
  {
    id: { primaryKey: "folder-001" },
    name: "Test Folder",
    added: new Date("2026-01-01T00:00:00Z"),
    modified: new Date("2026-01-02T00:00:00Z"),
    active: true,
    effectiveActive: true,
    status: { name: "Active" },
    parent: null,
  },
]);

vi.stubGlobal("Perspective", {
  all: [
    {
      identifier: "perspective-001",
      name: "Forecast",
    },
  ],
});

// Mock Task.Status for ts() helper
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

  it("rr() extracts repetition rule", function () {
    var rule = { ruleString: "FREQ=DAILY", scheduleType: { name: "Due" } };
    expect(bridge.rr(rule)).toEqual({
      ruleString: "FREQ=DAILY",
      scheduleType: "Due",
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

  it("ts() returns null for unknown status", function () {
    expect(bridge.ts("Unknown")).toBeNull();
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
          return '{"operation": "snapshot", "params": {}}';
        },
      },
    });

    var result = bridge.readRequest("/tmp/ipc", "123_uuid");
    expect(URL.fromPath).toHaveBeenCalledWith(
      "/tmp/ipc/123_uuid.request.json",
      false,
    );
    expect(mockFromURL).toHaveBeenCalled();
    expect(result).toEqual({ operation: "snapshot", params: {} });
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

describe("handleSnapshot", function () {
  it("collects all 5 entity types and returns structured data", function () {
    var result = bridge.handleSnapshot();

    // Tasks
    expect(result.tasks).toHaveLength(1);
    expect(result.tasks[0].id).toBe("task-001");
    expect(result.tasks[0].name).toBe("Test Task");
    expect(result.tasks[0].project).toBe("proj-001");
    expect(result.tasks[0].tags).toEqual(["tag1"]);

    // Projects
    expect(result.projects).toHaveLength(1);
    expect(result.projects[0].id).toBe("proj-001");
    expect(result.projects[0].name).toBe("Test Project");

    // Tags
    expect(result.tags).toHaveLength(1);
    expect(result.tags[0].id).toBe("tag-001");
    expect(result.tags[0].name).toBe("tag1");

    // Folders
    expect(result.folders).toHaveLength(1);
    expect(result.folders[0].id).toBe("folder-001");
    expect(result.folders[0].name).toBe("Test Folder");

    // Perspectives
    expect(result.perspectives).toHaveLength(1);
    expect(result.perspectives[0].id).toBe("perspective-001");
    expect(result.perspectives[0].name).toBe("Forecast");
  });
});

describe("dispatch", function () {
  beforeEach(function () {
    vi.clearAllMocks();
    // Default: readRequest returns snapshot operation
    mockFromURL.mockReturnValue({
      contents: {
        toString: function () {
          return '{"operation": "snapshot", "params": {}}';
        },
      },
    });
  });

  it("routes snapshot operation to handleSnapshot and writes success response", function () {
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
          return '{"operation": "snapshot", "params": {}}';
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
