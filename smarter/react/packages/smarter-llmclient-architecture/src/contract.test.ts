/**
 * The contract between this package and the Smarter backend: contract/llmclient-architecture.schema.json, which the
 * backend generates from its Pydantic model (smarter.lib.manifest.models.SAMDependencyTreeNode).
 *
 * - src/contract.gen.ts, the TypeScript types, must be generated from the current schema.
 * - The test fixtures, which the stories and tests use as the trees, must match it, so that the tests can't pass
 *   against data that the backend never sends.
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import Ajv2020 from "ajv/dist/2020";
import { describe, expect, it } from "vitest";

import { leafTree, lockedTree, stackademyTree } from "@/mocks/fixtures";

const root = path.resolve(import.meta.dirname, "..");
const schema = JSON.parse(fs.readFileSync(path.join(root, "contract", "llmclient-architecture.schema.json"), "utf-8"));
const ajv = new Ajv2020({ strict: false, allErrors: true });
ajv.addSchema(schema);

/** The errors of data against a definition of the schema: none if it matches. */
function errors(definition: string, data: unknown): string[] {
  const validate = ajv.getSchema(`${schema.$id}#/$defs/${definition}`);
  if (!validate) throw new Error(`The schema has no definition ${definition}`);
  return validate(data)
    ? []
    : (validate.errors ?? []).map((error) => `${definition}${error.instancePath} ${error.message}`);
}

describe("the contract's TypeScript types", () => {
  it("are generated from the current schema", () => {
    expect(() =>
      execFileSync(process.execPath, [path.join(root, "scripts", "contract-types.mjs"), "--check"], { stdio: "pipe" }),
    ).not.toThrow();
  });
});

describe("the test fixtures match the contract", () => {
  it("trees", () => {
    for (const tree of [stackademyTree, leafTree, lockedTree]) {
      expect(errors("SAMDependencyTreeNode", tree)).toEqual([]);
    }
  });

  it("rejects what the backend never sends", () => {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { icon, ...withoutIcon } = leafTree;
    expect(errors("SAMDependencyTreeNode", withoutIcon)).not.toEqual([]);
    expect(errors("SAMDependencyTreeNode", { ...leafTree, readable: "yes" })).not.toEqual([]);
  });
});
