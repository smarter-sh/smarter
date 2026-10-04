/**
 * Manifest validation for the editor: YAML syntax errors, from js-yaml, and the errors of the
 * manifest's SAM Pydantic model, from the cli api's validate command. Each error has a
 * position in the YAML, so that the editor can mark it.
 */
import { EVENT_ID, getScalarValue, load, parseEvents, YAMLException, type Event, type ScalarEvent } from "js-yaml";
import type { SessionContext } from "@smarter/common";
import { fetchDjangoUrl } from "@smarter/common";

import { loggerPrefix } from "@/const";

export type ManifestError = {
  /** "yaml" for a syntax error, "sam" for an error of the manifest's SAM model. */
  source: "yaml" | "sam";
  message: string;
  /** Zero-based offset of the error in the YAML. */
  offset: number;
  /** The path of the invalid value, e.g. ["spec", "config", "stage"]. Empty for a syntax error. */
  loc: string[];
};

/** Return the offset of a js-yaml error's mark, from its zero-based line and column. */
function markOffset(yaml: string, mark?: { line: number; column: number }): number {
  if (!mark) return 0;
  const lines = yaml.split("\n");
  const line = Math.min(Math.max(mark.line, 0), lines.length - 1);
  const lineStart = lines.slice(0, line).reduce((total, text) => total + text.length + 1, 0);
  return lineStart + Math.min(Math.max(mark.column, 0), lines[line].length);
}

/** Return the YAML's syntax errors: none, or the first one that js-yaml finds. */
export function syntaxErrors(yaml: string): ManifestError[] {
  try {
    load(yaml);
    return [];
  } catch (error) {
    if (error instanceof YAMLException) {
      return [{ source: "yaml", message: error.reason, offset: markOffset(yaml, error.mark), loc: [] }];
    }
    return [{ source: "yaml", message: String(error), offset: 0, loc: [] }];
  }
}

type Container = { kind: "mapping"; path: string[]; key: string | null } | { kind: "sequence"; path: string[]; index: number };

/** Where a key is in the YAML: its key's offset, and the end of its value, if its value is a scalar. */
export type YamlKey = {
  start: number;
  end?: number;
};

/**
 * Return where each key is in the YAML, by its path, e.g. "spec.config.stage". A sequence's
 * items are numbered, e.g. "metadata.tags.0".
 */
export function yamlKeys(yaml: string): Map<string, YamlKey> {
  const keys = new Map<string, YamlKey>();
  let events: Event[];
  try {
    events = parseEvents(yaml, {});
  } catch {
    return keys;
  }
  const stack: Container[] = [];

  // the path of the next value in the innermost container, and record where a sequence item is.
  const nextValuePath = (offset: number): string[] | null => {
    const top = stack[stack.length - 1];
    if (!top) return [];
    if (top.kind === "sequence") {
      const path = [...top.path, String(top.index)];
      top.index += 1;
      if (!keys.has(path.join("."))) keys.set(path.join("."), { start: offset });
      return path;
    }
    if (top.key === null) return null; // a key, not a value
    const path = [...top.path, top.key];
    top.key = null;
    return path;
  };

  for (const event of events) {
    if (event.type === EVENT_ID.MAPPING || event.type === EVENT_ID.SEQUENCE) {
      const path = nextValuePath(event.start) ?? [];
      stack.push(event.type === EVENT_ID.MAPPING ? { kind: "mapping", path, key: null } : { kind: "sequence", path, index: 0 });
    } else if (event.type === EVENT_ID.SCALAR) {
      const scalar = event as ScalarEvent;
      const top = stack[stack.length - 1];
      if (top?.kind === "mapping" && top.key === null) {
        // a mapping's key: record where it is.
        top.key = getScalarValue(yaml, scalar);
        const path = [...top.path, top.key];
        if (!keys.has(path.join("."))) keys.set(path.join("."), { start: scalar.valueStart });
      } else {
        // a scalar value: record where it ends.
        const path = nextValuePath(scalar.valueStart);
        const key = path ? keys.get(path.join(".")) : undefined;
        if (key && key.end === undefined) key.end = scalar.valueEnd;
      }
    } else if (event.type === EVENT_ID.ALIAS) {
      nextValuePath(0);
    } else if (event.type === EVENT_ID.POP) {
      stack.pop();
    }
  }
  return keys;
}

/** Return the offset of each key in the YAML, by its path. See {@link yamlKeys}. */
export function keyOffsets(yaml: string): Map<string, number> {
  return new Map([...yamlKeys(yaml)].map(([path, key]) => [path, key.start]));
}

/** Return the offset of a path in the YAML, or of its nearest parent that is there, or 0. */
export function locOffset(offsets: Map<string, number>, loc: string[]): number {
  for (let n = loc.length; n > 0; n--) {
    const offset = offsets.get(loc.slice(0, n).join("."));
    if (offset !== undefined) return offset;
  }
  return 0;
}

type ValidateResponseBody = {
  data?: { valid?: boolean; errors?: Array<{ loc?: string[]; message?: string }> };
};

/**
 * Return the errors of the manifest's SAM model, from the cli api's validate command, which
 * validates the manifest without saving it.
 */
export async function samErrors(
  sessionContext: SessionContext,
  validateApiUrl: string,
  yaml: string,
  manifest: unknown,
): Promise<ManifestError[]> {
  const response = await fetchDjangoUrl(sessionContext, validateApiUrl, JSON.stringify(manifest));
  const body = (await response.json().catch(() => null)) as ValidateResponseBody | null;
  if (!response.ok || !body?.data) {
    console.warn(loggerPrefix, `samErrors() ${validateApiUrl} returned ${response.status}:`, body);
    return [];
  }
  const offsets = keyOffsets(yaml);
  return (body.data.errors ?? []).map((error) => {
    const loc = error.loc ?? [];
    return { source: "sam", message: error.message || "Invalid value", offset: locOffset(offsets, loc), loc };
  });
}
