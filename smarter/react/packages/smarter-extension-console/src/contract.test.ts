/**
 * The contract between this app and the Smarter backend: contract/extension-console.schema.json,
 * which the backend generates from its Pydantic models (smarter.apps.llmtool.extension.contract).
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

import {
  accounts,
  action,
  brokenDetail,
  detail,
  disabledDetail,
  disabledRegistry,
  listResponse,
  registryResponse,
} from "@/mocks/fixtures";

const root = path.resolve(import.meta.dirname, "..");
const schema = JSON.parse(fs.readFileSync(path.join(root, "contract", "extension-console.schema.json"), "utf-8"));
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
    expect(errors("ExtensionListResponse", listResponse)).toEqual([]);
    expect(errors("RegistryResponse", registryResponse)).toEqual([]);
    expect(errors("RegistryResponse", disabledRegistry)).toEqual([]);
    expect(errors("AccountsResponse", { objects: accounts })).toEqual([]);
  });

  it("details and actions", () => {
    for (const extension of [detail, disabledDetail, brokenDetail]) {
      expect(errors("ExtensionDetailResponse", { extension })).toEqual([]);
    }
    expect(errors("ActionResponse", action("Done."))).toEqual([]);
    expect(errors("ActionResponse", action("Uninstalled.", null))).toEqual([]);
    expect(errors("ErrorResponse", { error: "Database unavailable" })).toEqual([]);
  });

  it("rejects what the backend never sends", () => {
    expect(errors("ExtensionListResponse", { objects: [] })).not.toEqual([]);
  });
});
