/**
 * The contract between the Extensions tab and the Smarter backend: contract/extension-list.schema.json,
 * which the backend generates from its Pydantic models (smarter.apps.llmtool.views.listview.contract).
 *
 * - src/contract.gen.ts, the TypeScript types, must be generated from the current schema.
 * - The test fixtures, which the stories and tests use as the api's responses, must match it, so that
 *   the tests can't pass against responses that the backend never sends.
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import Ajv2020 from "ajv/dist/2020";
import { describe, expect, it } from "vitest";

import { extensionObjects, extensionPage, makeExtension } from "@/mocks/fixtures";

const root = path.resolve(import.meta.dirname, "..");
const schema = JSON.parse(fs.readFileSync(path.join(root, "contract", "extension-list.schema.json"), "utf-8"));
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
  it("lists", () => {
    expect(errors("ExtensionListPage", extensionPage())).toEqual([]);
    expect(errors("ExtensionListPage", extensionPage([]))).toEqual([]);
    for (const extension of extensionObjects) {
      expect(errors("ExtensionListItem", extension)).toEqual([]);
    }
  });

  it("rejects what the backend never sends", () => {
    expect(errors("ExtensionListPage", { objects: extensionObjects })).not.toEqual([]);
    expect(errors("ExtensionListItem", { ...makeExtension(1), canDelete: false })).not.toEqual([]);
    expect(errors("ExtensionListItem", makeExtension(1, { trustBadge: "trusted" as never }))).not.toEqual([]);
  });
});
