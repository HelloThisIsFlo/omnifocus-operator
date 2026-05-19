import { describe, it, expect } from "vitest";
import {
  mergeOmnifocusOperator,
  parseUserConfig,
  computeDiffLines,
  OMNIFOCUS_OPERATOR_ENTRY,
  ENTRY_KEY,
} from "../../docs/js/config-merger.js";

// ─── Helpers ────────────────────────────────────────────────────────────────

function expectValidMerge(result) {
  expect(result.ok).toBe(true);
  expect(result.status).toBe("merged");
  expect(typeof result.merged).toBe("string");
  // Round-trip must succeed.
  expect(() => JSON.parse(result.merged)).not.toThrow();
}

function entryFrom(result) {
  return JSON.parse(result.merged).mcpServers[ENTRY_KEY];
}

// ─── Input handling ─────────────────────────────────────────────────────────

describe("input handling", () => {
  it("treats empty string as {}", () => {
    const r = mergeOmnifocusOperator("");
    expectValidMerge(r);
    expect(JSON.parse(r.merged)).toEqual({
      mcpServers: { [ENTRY_KEY]: { command: "uvx", args: [ENTRY_KEY] } },
    });
  });

  it("treats whitespace-only string as {}", () => {
    const r = mergeOmnifocusOperator("   \n\t   ");
    expectValidMerge(r);
    expect(Object.keys(JSON.parse(r.merged).mcpServers)).toEqual([ENTRY_KEY]);
  });

  it("treats null as {}", () => {
    const r = mergeOmnifocusOperator(null);
    expectValidMerge(r);
    expect(Object.keys(JSON.parse(r.merged).mcpServers)).toEqual([ENTRY_KEY]);
  });

  it("treats undefined as {}", () => {
    const r = mergeOmnifocusOperator(undefined);
    expectValidMerge(r);
    expect(Object.keys(JSON.parse(r.merged).mcpServers)).toEqual([ENTRY_KEY]);
  });

  it("rejects non-string, non-null inputs", () => {
    const r = mergeOmnifocusOperator(42);
    expect(r.ok).toBe(false);
    expect(r.status).toBe("parse-error");
  });

  it("handles a plain {} input", () => {
    const r = mergeOmnifocusOperator("{}");
    expectValidMerge(r);
    const parsed = JSON.parse(r.merged);
    expect(parsed.mcpServers[ENTRY_KEY]).toEqual({
      command: "uvx",
      args: [ENTRY_KEY],
    });
  });

  it("rejects a top-level array", () => {
    const r = mergeOmnifocusOperator("[]");
    expect(r.ok).toBe(false);
    expect(r.status).toBe("not-an-object");
    expect(r.error).toMatch(/object/i);
  });

  it("rejects a top-level string", () => {
    const r = mergeOmnifocusOperator('"hello"');
    expect(r.ok).toBe(false);
    expect(r.status).toBe("not-an-object");
  });

  it("rejects a top-level number", () => {
    const r = mergeOmnifocusOperator("42");
    expect(r.ok).toBe(false);
    expect(r.status).toBe("not-an-object");
  });

  it("rejects a top-level boolean", () => {
    const r = mergeOmnifocusOperator("true");
    expect(r.ok).toBe(false);
    expect(r.status).toBe("not-an-object");
  });

  it("rejects a top-level JSON null", () => {
    const r = mergeOmnifocusOperator("null");
    expect(r.ok).toBe(false);
    expect(r.status).toBe("not-an-object");
  });

  it("rejects invalid JSON: trailing comma", () => {
    const r = mergeOmnifocusOperator('{ "a": 1, }');
    expect(r.ok).toBe(false);
    expect(r.status).toBe("parse-error");
    expect(typeof r.error).toBe("string");
    expect(r.error.length).toBeGreaterThan(0);
  });

  it("rejects invalid JSON: missing quote", () => {
    const r = mergeOmnifocusOperator('{ "a: 1 }');
    expect(r.ok).toBe(false);
    expect(r.status).toBe("parse-error");
  });

  it("rejects invalid JSON: unmatched brace", () => {
    const r = mergeOmnifocusOperator('{ "a": { "b": 1 }');
    expect(r.ok).toBe(false);
    expect(r.status).toBe("parse-error");
  });

  it("rejects JSON5-style comments", () => {
    const r = mergeOmnifocusOperator('{\n  // a comment\n  "a": 1\n}');
    expect(r.ok).toBe(false);
    expect(r.status).toBe("parse-error");
  });

  it("rejects JSON5-style unquoted keys", () => {
    const r = mergeOmnifocusOperator("{ a: 1 }");
    expect(r.ok).toBe(false);
    expect(r.status).toBe("parse-error");
  });
});

// ─── Existing config shapes ─────────────────────────────────────────────────

describe("existing config shapes", () => {
  it("adds omnifocus-operator to empty mcpServers", () => {
    const r = mergeOmnifocusOperator('{ "mcpServers": {} }');
    expectValidMerge(r);
    expect(entryFrom(r)).toEqual({ command: "uvx", args: [ENTRY_KEY] });
  });

  it("adds omnifocus-operator alongside another server", () => {
    const input = JSON.stringify({
      mcpServers: {
        "other-server": { command: "node", args: ["server.js"] },
      },
    });
    const r = mergeOmnifocusOperator(input);
    expectValidMerge(r);
    const parsed = JSON.parse(r.merged);
    // Both servers present.
    expect(parsed.mcpServers["other-server"]).toEqual({
      command: "node",
      args: ["server.js"],
    });
    expect(parsed.mcpServers[ENTRY_KEY]).toEqual({
      command: "uvx",
      args: [ENTRY_KEY],
    });
    expect(Object.keys(parsed.mcpServers)).toHaveLength(2);
  });

  it("returns already-configured if omnifocus-operator exists", () => {
    const input = JSON.stringify({
      mcpServers: {
        [ENTRY_KEY]: { command: "uvx", args: [ENTRY_KEY] },
      },
    });
    const r = mergeOmnifocusOperator(input);
    expect(r.ok).toBe(true);
    expect(r.status).toBe("already-configured");
    // Do not return a "merged" string in this case.
    expect(r.merged).toBeUndefined();
  });

  it("treats omnifocus-operator with a non-canonical value as already-configured (no silent overwrite)", () => {
    const input = JSON.stringify({
      mcpServers: {
        [ENTRY_KEY]: { command: "different", args: ["something-else"] },
      },
    });
    const r = mergeOmnifocusOperator(input);
    expect(r.ok).toBe(true);
    expect(r.status).toBe("already-configured");
  });

  it("creates mcpServers and preserves other top-level keys", () => {
    const input = JSON.stringify({ otherKey: "value", another: 42 });
    const r = mergeOmnifocusOperator(input);
    expectValidMerge(r);
    const parsed = JSON.parse(r.merged);
    expect(parsed.otherKey).toBe("value");
    expect(parsed.another).toBe(42);
    expect(parsed.mcpServers[ENTRY_KEY]).toEqual({
      command: "uvx",
      args: [ENTRY_KEY],
    });
  });

  it("rejects mcpServers: null (does not silently replace)", () => {
    // Decision: null is a malformed config — surface the error rather than
    // silently fixing it. See module header.
    const r = mergeOmnifocusOperator('{ "mcpServers": null }');
    expect(r.ok).toBe(false);
    expect(r.status).toBe("invalid-mcp-servers");
    expect(r.error).toMatch(/object/i);
  });

  it("rejects mcpServers: string", () => {
    const r = mergeOmnifocusOperator('{ "mcpServers": "hello" }');
    expect(r.ok).toBe(false);
    expect(r.status).toBe("invalid-mcp-servers");
    expect(r.error).toMatch(/object/i);
  });

  it("rejects mcpServers: number", () => {
    const r = mergeOmnifocusOperator('{ "mcpServers": 42 }');
    expect(r.ok).toBe(false);
    expect(r.status).toBe("invalid-mcp-servers");
  });

  it("rejects mcpServers: boolean", () => {
    const r = mergeOmnifocusOperator('{ "mcpServers": true }');
    expect(r.ok).toBe(false);
    expect(r.status).toBe("invalid-mcp-servers");
  });

  it("rejects mcpServers: array", () => {
    const r = mergeOmnifocusOperator('{ "mcpServers": [] }');
    expect(r.ok).toBe(false);
    expect(r.status).toBe("invalid-mcp-servers");
    expect(r.error).toMatch(/object/i);
  });
});

// ─── Diff highlighting ──────────────────────────────────────────────────────

describe("diff highlighting", () => {
  it("marks new entry lines as added", () => {
    const r = mergeOmnifocusOperator('{ "mcpServers": {} }');
    expectValidMerge(r);
    const addedLines = r.lines.filter((l) => l.added).map((l) => l.text);
    // The added block contains the key, the command, the args, and the closing brace.
    expect(addedLines.length).toBeGreaterThanOrEqual(4);
    expect(addedLines.some((t) => t.includes(`"${ENTRY_KEY}"`))).toBe(true);
    expect(addedLines.some((t) => t.includes('"command"'))).toBe(true);
    expect(addedLines.some((t) => t.includes('"args"'))).toBe(true);
  });

  it("does NOT mark lines of existing entries as added", () => {
    const input = JSON.stringify({
      mcpServers: {
        "other-server": { command: "node", args: ["server.js"] },
      },
    });
    const r = mergeOmnifocusOperator(input);
    expectValidMerge(r);
    // None of the "added" lines should reference other-server.
    const addedTexts = r.lines.filter((l) => l.added).map((l) => l.text);
    expect(addedTexts.every((t) => !t.includes("other-server"))).toBe(true);
    expect(addedTexts.every((t) => !t.includes("server.js"))).toBe(true);
  });

  it("returns all lines in order and reassembles to merged output", () => {
    const input = JSON.stringify({ mcpServers: { "other-server": { command: "x" } } });
    const r = mergeOmnifocusOperator(input);
    expectValidMerge(r);
    const reassembled = r.lines.map((l) => l.text).join("\n");
    expect(reassembled).toBe(r.merged);
  });

  it("handles brace depth correctly when other servers have nested objects", () => {
    // Put a deeply nested other-server BEFORE omnifocus-operator (alphabetical
    // order: "another" < "omnifocus-operator") so we exercise the case where
    // the merger has to skip over braces before hitting the new entry.
    const input = JSON.stringify({
      mcpServers: {
        another: {
          command: "node",
          args: ["s.js"],
          env: { DEEP: { NESTED: { VAR: "value" } } },
        },
      },
    });
    const r = mergeOmnifocusOperator(input);
    expectValidMerge(r);
    const addedTexts = r.lines.filter((l) => l.added).map((l) => l.text);
    // None of the added lines should reference the "another" server or its nested env.
    expect(addedTexts.every((t) => !t.includes("another"))).toBe(true);
    expect(addedTexts.every((t) => !t.includes("DEEP"))).toBe(true);
    expect(addedTexts.every((t) => !t.includes("NESTED"))).toBe(true);
    // The added block ends after omnifocus-operator closes — verify subsequent
    // lines (the closing braces of mcpServers + root object) are NOT marked.
    const lastAddedIndex = r.lines.reduce(
      (idx, l, i) => (l.added ? i : idx),
      -1,
    );
    // There should be at least one un-added line after the added block (the
    // closing brace of mcpServers and the root object).
    expect(lastAddedIndex).toBeLessThan(r.lines.length - 1);
  });

  it("handles a server defined AFTER omnifocus-operator alphabetically", () => {
    // "zeta" sorts after "omnifocus-operator", so when stringified the entry
    // comes first in output. The diff tracker must close cleanly before "zeta".
    // Note: JSON.stringify preserves insertion order, so we control placement.
    const cfg = { mcpServers: {} };
    cfg.mcpServers["zeta"] = {
      command: "z",
      args: [],
      env: { A: { B: 1 } },
    };
    const r = mergeOmnifocusOperator(JSON.stringify(cfg));
    expectValidMerge(r);
    // After inserting omnifocus-operator, zeta is still present.
    const parsed = JSON.parse(r.merged);
    expect(parsed.mcpServers.zeta).toBeDefined();
    // zeta lines must NOT be marked as added.
    const addedTexts = r.lines.filter((l) => l.added).map((l) => l.text);
    expect(addedTexts.every((t) => !t.includes("zeta"))).toBe(true);
  });
});

// ─── Output format ──────────────────────────────────────────────────────────

describe("output format", () => {
  it("produces valid JSON that round-trips", () => {
    const r = mergeOmnifocusOperator(
      JSON.stringify({
        mcpServers: { "other-server": { command: "x", args: ["y"] } },
      }),
    );
    expectValidMerge(r);
    const parsed = JSON.parse(r.merged);
    expect(parsed).toEqual({
      mcpServers: {
        "other-server": { command: "x", args: ["y"] },
        [ENTRY_KEY]: { command: "uvx", args: [ENTRY_KEY] },
      },
    });
  });

  it("uses 2-space indentation matching JSON.stringify(obj, null, 2)", () => {
    const r = mergeOmnifocusOperator("{}");
    expectValidMerge(r);
    const parsed = JSON.parse(r.merged);
    expect(r.merged).toBe(JSON.stringify(parsed, null, 2));
    // First indented line begins with exactly two spaces.
    const indentedLine = r.merged.split("\n").find((l) => l.startsWith(" "));
    expect(indentedLine.startsWith("  ")).toBe(true);
    expect(indentedLine.startsWith("   ")).toBe(false);
  });

  it("uses the exact key 'omnifocus-operator'", () => {
    const r = mergeOmnifocusOperator("{}");
    expectValidMerge(r);
    const parsed = JSON.parse(r.merged);
    expect(Object.keys(parsed.mcpServers)).toContain("omnifocus-operator");
    expect(Object.keys(parsed.mcpServers)).not.toContain("omnifocusOperator");
    expect(Object.keys(parsed.mcpServers)).not.toContain("omnifocus_operator");
  });

  it("uses the exact entry value { command: 'uvx', args: ['omnifocus-operator'] }", () => {
    const r = mergeOmnifocusOperator("{}");
    expectValidMerge(r);
    const entry = JSON.parse(r.merged).mcpServers[ENTRY_KEY];
    expect(entry).toEqual({ command: "uvx", args: ["omnifocus-operator"] });
    // Exact key set — no extra keys.
    expect(Object.keys(entry).sort()).toEqual(["args", "command"]);
  });

  it("does not mutate the canonical entry constant", () => {
    const r = mergeOmnifocusOperator("{}");
    expectValidMerge(r);
    // Mutate the merged result and confirm the constant is untouched.
    const parsed = JSON.parse(r.merged);
    parsed.mcpServers[ENTRY_KEY].args.push("mutated");
    expect(OMNIFOCUS_OPERATOR_ENTRY.args).toEqual([ENTRY_KEY]);
    expect(OMNIFOCUS_OPERATOR_ENTRY.command).toBe("uvx");
  });
});

// ─── Realistic configs ──────────────────────────────────────────────────────

describe("realistic configs", () => {
  it("merges into a config with 4 other servers and nested env objects", () => {
    const input = JSON.stringify(
      {
        mcpServers: {
          filesystem: {
            command: "npx",
            args: [
              "-y",
              "@modelcontextprotocol/server-filesystem",
              "/Users/flo/Documents",
            ],
          },
          github: {
            command: "npx",
            args: ["-y", "@modelcontextprotocol/server-github"],
            env: { GITHUB_PERSONAL_ACCESS_TOKEN: "ghp_xxx" },
          },
          time: {
            command: "uvx",
            args: ["mcp-server-time"],
          },
          fetch: {
            command: "uvx",
            args: ["mcp-server-fetch"],
          },
        },
      },
      null,
      2,
    );
    const r = mergeOmnifocusOperator(input);
    expectValidMerge(r);
    const parsed = JSON.parse(r.merged);
    // All 4 originals present.
    expect(Object.keys(parsed.mcpServers).sort()).toEqual(
      ["fetch", "filesystem", "github", "omnifocus-operator", "time"].sort(),
    );
    // omnifocus-operator entry value is canonical.
    expect(parsed.mcpServers[ENTRY_KEY]).toEqual({
      command: "uvx",
      args: [ENTRY_KEY],
    });
    // Other entries are unmodified.
    expect(parsed.mcpServers.github.env).toEqual({
      GITHUB_PERSONAL_ACCESS_TOKEN: "ghp_xxx",
    });
    expect(parsed.mcpServers.filesystem.args).toContain("/Users/flo/Documents");
    // Diff lines: only the omnifocus-operator block is marked added.
    const addedTexts = r.lines.filter((l) => l.added).map((l) => l.text);
    expect(addedTexts.every((t) => !t.includes("github"))).toBe(true);
    expect(addedTexts.every((t) => !t.includes("filesystem"))).toBe(true);
    expect(addedTexts.every((t) => !t.includes("fetch"))).toBe(true);
    expect(addedTexts.every((t) => !t.includes("time"))).toBe(true);
    expect(addedTexts.every((t) => !t.includes("GITHUB_PERSONAL"))).toBe(true);
  });

  it("preserves a non-mcpServers top-level key in a realistic config", () => {
    const input = JSON.stringify({
      globalShortcut: "Cmd+Shift+Space",
      mcpServers: {
        github: { command: "npx", args: ["@gh"] },
      },
    });
    const r = mergeOmnifocusOperator(input);
    expectValidMerge(r);
    const parsed = JSON.parse(r.merged);
    expect(parsed.globalShortcut).toBe("Cmd+Shift+Space");
    expect(parsed.mcpServers.github).toEqual({ command: "npx", args: ["@gh"] });
    expect(parsed.mcpServers[ENTRY_KEY]).toEqual({
      command: "uvx",
      args: [ENTRY_KEY],
    });
  });
});

// ─── Lower-level helpers ────────────────────────────────────────────────────

describe("parseUserConfig", () => {
  it("returns {} for null/undefined/empty", () => {
    expect(parseUserConfig(null)).toEqual({ ok: true, value: {} });
    expect(parseUserConfig(undefined)).toEqual({ ok: true, value: {} });
    expect(parseUserConfig("")).toEqual({ ok: true, value: {} });
    expect(parseUserConfig("   ")).toEqual({ ok: true, value: {} });
  });

  it("parses valid JSON", () => {
    const r = parseUserConfig('{ "a": 1 }');
    expect(r.ok).toBe(true);
    expect(r.value).toEqual({ a: 1 });
  });

  it("returns ok:false with an error message on invalid JSON", () => {
    const r = parseUserConfig("{ broken");
    expect(r.ok).toBe(false);
    expect(typeof r.error).toBe("string");
    expect(r.error.length).toBeGreaterThan(0);
  });

  it("rejects non-string non-null input types", () => {
    expect(parseUserConfig(42).ok).toBe(false);
    expect(parseUserConfig({}).ok).toBe(false);
    expect(parseUserConfig([]).ok).toBe(false);
    expect(parseUserConfig(true).ok).toBe(false);
  });
});

describe("computeDiffLines", () => {
  it("marks no lines when input has no omnifocus-operator", () => {
    const json = JSON.stringify({ mcpServers: { x: { command: "y" } } }, null, 2);
    const lines = computeDiffLines(json);
    expect(lines.every((l) => !l.added)).toBe(true);
  });

  it("marks exactly the omnifocus-operator block as added", () => {
    const json = JSON.stringify(
      {
        mcpServers: {
          a: { command: "x" },
          [ENTRY_KEY]: { command: "uvx", args: [ENTRY_KEY] },
          z: { command: "y" },
        },
      },
      null,
      2,
    );
    const lines = computeDiffLines(json);
    const addedTexts = lines.filter((l) => l.added).map((l) => l.text);
    expect(addedTexts.some((t) => t.includes(`"${ENTRY_KEY}"`))).toBe(true);
    // Sanity: no added line references the "a" or "z" servers.
    // (Note: the closing brace `}` of omnifocus-operator block IS added.)
    expect(addedTexts.every((t) => !t.includes('"a"'))).toBe(true);
    expect(addedTexts.every((t) => !t.includes('"z"'))).toBe(true);
  });
});
