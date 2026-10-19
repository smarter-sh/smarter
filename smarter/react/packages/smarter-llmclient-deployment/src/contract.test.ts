/**
 * The contract between this app and the Smarter backend: contract/llmclient-deployment.schema.json,
 * which the backend generates from its Pydantic models (smarter.apps.llmclient.views.deployment_contract).
 *
 * - src/contract.gen.ts, the TypeScript types, must be generated from the current schema.
 * - The test fixtures, which the stories and tests use as the pages and the api's responses, must match
 *   it, so that the tests can't pass against data that the backend never sends.
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import Ajv2020 from "ajv/dist/2020";
import { describe, expect, it } from "vitest";

import {
  attachedResponse,
  authenticatedPage,
  createdResponse,
  detachedResponse,
  duplicateNameError,
  inactiveKeyPage,
  notDeployedPage,
  publicPage,
  sharedPage,
  workbenchPage,
} from "@/mocks/fixtures";

const root = path.resolve(import.meta.dirname, "..");
const schema = JSON.parse(fs.readFileSync(path.join(root, "contract", "llmclient-deployment.schema.json"), "utf-8"));
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
  it("pages", () => {
    for (const page of [workbenchPage, publicPage, notDeployedPage, authenticatedPage, inactiveKeyPage, sharedPage]) {
      expect(errors("LLMClientDeploymentPage", page)).toEqual([]);
    }
  });

  it("api responses", () => {
    for (const response of [createdResponse, attachedResponse, detachedResponse]) {
      expect(errors("ApiKeyActionResponse", response)).toEqual([]);
    }
    expect(errors("ErrorResponse", duplicateNameError)).toEqual([]);
    expect(errors("CreateApiKeyRequest", { name: "my_key" })).toEqual([]);
    expect(errors("AttachApiKeyRequest", { keyId: workbenchPage.apiKeys!.apiKeys[0].keyId })).toEqual([]);
  });

  it("rejects what the backend never sends", () => {
    expect(errors("LLMClientDeploymentPage", { ...publicPage, mode: "admin" })).not.toEqual([]);
    expect(errors("ErrorResponse", { error: "x", code: "nope" })).not.toEqual([]);
  });
});
