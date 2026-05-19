// ─── Config Merger ──────────────────────────────────────────────────────────
//
// Pure-function module for merging an `omnifocus-operator` entry into a
// user's existing `claude_desktop_config.json`.
//
// This module has NO DOM access. The landing page (`docs/index.html`) imports
// it and handles all rendering / clipboard / DOM updates.
//
// The result shape is:
//
//   Success (new entry added):
//     {
//       ok: true,
//       status: "merged",
//       merged: "<json string with 2-space indent>",
//       config: <merged object>,
//       lines: [{ text: string, added: boolean }, ...],
//     }
//
//   Success (already present, no changes):
//     {
//       ok: true,
//       status: "already-configured",
//     }
//
//   Failure:
//     {
//       ok: false,
//       status: "<error-code>",
//       error: "<human-readable message>",
//     }
//
// Error codes:
//   - "parse-error"   — JSON.parse failed (also covers JSON5 / comments)
//   - "not-an-object" — top-level value isn't a plain object (array, scalar, null)
//   - "invalid-mcp-servers" — `mcpServers` key exists but isn't a plain object

/** The canonical entry value we always merge in. */
export const OMNIFOCUS_OPERATOR_ENTRY = Object.freeze({
  command: "uvx",
  args: Object.freeze(["omnifocus-operator"]),
});

/** The key under `mcpServers` we manage. */
export const ENTRY_KEY = "omnifocus-operator";

/**
 * Return true if value is a non-null, non-array object (a plain object-like).
 */
function isPlainObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Parse the user's config text.
 *
 * Treats null / undefined / empty string / whitespace-only as `{}`.
 *
 * Returns either { ok: true, value } or { ok: false, error }.
 */
export function parseUserConfig(input) {
  if (input === null || input === undefined) {
    return { ok: true, value: {} };
  }
  if (typeof input !== "string") {
    return {
      ok: false,
      error: "Input must be a string (or null/undefined).",
    };
  }
  const trimmed = input.trim();
  if (trimmed === "") {
    return { ok: true, value: {} };
  }
  try {
    return { ok: true, value: JSON.parse(trimmed) };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

/**
 * Build a fresh deep-copy of the entry value so callers can't mutate the frozen constant.
 */
function freshEntry() {
  return {
    command: OMNIFOCUS_OPERATOR_ENTRY.command,
    args: [...OMNIFOCUS_OPERATOR_ENTRY.args],
  };
}

/**
 * Compute the line-by-line "added" diff between the original-parsed config
 * (without the new entry) and the merged JSON-stringified output.
 *
 * Strategy: walk the merged JSON line-by-line. From the moment we hit a line
 * containing `"omnifocus-operator"`, we're "inside" the new entry. We track
 * brace depth — once it returns to 0 and the line contains `}`, we're done.
 *
 * This matches the logic that was inline in `docs/index.html`.
 */
export function computeDiffLines(mergedJson) {
  const lines = mergedJson.split("\n");
  let inNewEntry = false;
  let braceDepth = 0;
  const out = [];
  for (const line of lines) {
    if (!inNewEntry && line.includes(`"${ENTRY_KEY}"`)) {
      inNewEntry = true;
      braceDepth = 0;
    }
    if (inNewEntry) {
      braceDepth += (line.match(/\{/g) || []).length;
      braceDepth -= (line.match(/\}/g) || []).length;
      out.push({ text: line, added: true });
      if (braceDepth <= 0 && line.includes("}")) {
        inNewEntry = false;
      }
    } else {
      out.push({ text: line, added: false });
    }
  }
  return out;
}

/**
 * Merge `omnifocus-operator` into the user's `claude_desktop_config.json`.
 *
 * @param {string|null|undefined} input - Raw JSON text from the user.
 * @returns {object} Result object — see module header for shape.
 */
export function mergeOmnifocusOperator(input) {
  const parsed = parseUserConfig(input);
  if (!parsed.ok) {
    return {
      ok: false,
      status: "parse-error",
      error: parsed.error,
    };
  }

  const userConfig = parsed.value;

  if (!isPlainObject(userConfig)) {
    return {
      ok: false,
      status: "not-an-object",
      error:
        "That doesn't look like a Claude Desktop config — expected a top-level object.",
    };
  }

  // Validate mcpServers shape if present.
  // We accept missing/undefined → treat as fresh empty object.
  // We REJECT null, string, number, boolean, array → these indicate a malformed config.
  if (Object.prototype.hasOwnProperty.call(userConfig, "mcpServers")) {
    const mcp = userConfig.mcpServers;
    if (mcp !== undefined && !isPlainObject(mcp)) {
      return {
        ok: false,
        status: "invalid-mcp-servers",
        error:
          '"mcpServers" must be a JSON object — got ' +
          describeType(mcp) +
          " instead.",
      };
    }
  }

  if (!userConfig.mcpServers) {
    userConfig.mcpServers = {};
  }

  if (
    Object.prototype.hasOwnProperty.call(userConfig.mcpServers, ENTRY_KEY)
  ) {
    return {
      ok: true,
      status: "already-configured",
    };
  }

  userConfig.mcpServers[ENTRY_KEY] = freshEntry();
  const merged = JSON.stringify(userConfig, null, 2);
  const lines = computeDiffLines(merged);

  return {
    ok: true,
    status: "merged",
    merged,
    config: userConfig,
    lines,
  };
}

function describeType(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) return "an array";
  return "a " + typeof value;
}
