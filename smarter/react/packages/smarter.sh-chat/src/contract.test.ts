/**
 * The contract between Smarter Chat and the Smarter backend: contract/chat-contract.schema.json, which
 * the backend generates from its Pydantic models (smarter.apps.prompt.contract.models).
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
  apiErrorResponse,
  config,
  configV1,
  configWithDiagram,
  configWithHistory,
  configWithImages,
  configWithMath,
  progressEvents,
  promptErrorResponse,
  promptErrorResponseV1,
  promptMaxTokensResponse,
  promptMaxTokensResponseV1,
  promptResponse,
  promptResponseV1,
} from "@/mocks/fixtures";

const root = path.resolve(import.meta.dirname, "..");
const schema = JSON.parse(fs.readFileSync(path.join(root, "contract", "chat-contract.schema.json"), "utf-8"));
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

const envelope = { api: "smarter.sh/v1" };

describe("the contract's TypeScript types", () => {
  it("are generated from the current schema", () => {
    expect(() =>
      execFileSync(process.execPath, [path.join(root, "scripts", "contract-types.mjs"), "--check"], { stdio: "pipe" }),
    ).not.toThrow();
  });
});

describe("the test fixtures match the contract", () => {
  it("configurations, version 2", () => {
    for (const chatConfig of [config, configWithHistory, configWithImages, configWithDiagram, configWithMath]) {
      expect(errors("PromptChatApiConfigResponse", { data: chatConfig, ...envelope })).toEqual([]);
    }
  });

  it("configurations, version 1", () => {
    expect(errors("PromptChatApiConfigResponseV1", { data: configV1(configWithHistory), ...envelope })).toEqual([]);
  });

  it("prompt responses, version 2", () => {
    expect(errors("PromptChatApiPromptResponse", promptResponse())).toEqual([]);
    expect(errors("PromptChatApiPromptResponse", promptMaxTokensResponse())).toEqual([]);
    expect(errors("PromptChatApiPromptResponse", promptErrorResponse())).toEqual([]);
  });

  it("prompt responses, version 1", () => {
    for (const response of [promptResponseV1(), promptMaxTokensResponseV1()]) {
      expect(errors("PromptChatApiPromptResponseV1", response)).toEqual([]);
      expect(errors("PromptChatApiCompletionV1", JSON.parse(response.data.body))).toEqual([]);
    }
    const failure = promptErrorResponseV1();
    expect(errors("PromptChatApiPromptResponseV1", failure)).toEqual([]);
    expect(errors("PromptChatApiFailureV1", JSON.parse(failure.data.body))).toEqual([]);
  });

  it("progress events and errors", () => {
    for (const event of progressEvents) expect(errors("PromptChatApiProgressEvent", event)).toEqual([]);
    expect(errors("PromptChatApiProgressResult", { status: 200, response: promptResponse() })).toEqual([]);
    expect(errors("PromptChatApiErrorResponse", apiErrorResponse())).toEqual([]);
  });

  it("rejects a response that breaks the contract", () => {
    const validate = ajv.getSchema(`${schema.$id}#/$defs/PromptChatApiConfigResponse`)!;
    const { llmclient, ...withoutLLMClient } = config;
    expect(llmclient).toBeDefined();
    expect(validate({ data: withoutLLMClient, ...envelope })).toBe(false);
  });
});
