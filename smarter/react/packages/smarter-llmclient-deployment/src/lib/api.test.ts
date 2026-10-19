import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { ApiError, attachApiKey, createApiKey, detachApiKey } from "@/lib/api";
import {
  ATTACH_URL,
  CREATE_URL,
  attachedResponse,
  createdResponse,
  detachedResponse,
  duplicateNameError,
  makeApiKeys,
  session,
} from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

const apiKeys = makeApiKeys();

describe("the api key actions", () => {
  it("post to their urls, and return the page as it now is", async () => {
    let body: unknown = null;
    server.use(
      http.post(CREATE_URL, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(createdResponse);
      }),
      ...actionHandlers(),
    );
    expect(await createApiKey(session, apiKeys, { name: "my_new_key", attach: true })).toEqual(createdResponse);
    expect(body).toEqual({ name: "my_new_key", attach: true });
    expect(await attachApiKey(session, apiKeys, { keyId: "x" })).toEqual(attachedResponse);
    expect(await detachApiKey(session, apiKeys)).toEqual(detachedResponse);
  });

  it("throw the api's error, with its code", async () => {
    server.use(http.post(CREATE_URL, () => HttpResponse.json(duplicateNameError, { status: 400 })));
    const error = await createApiKey(session, apiKeys, { name: "my_site_chat" }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "duplicate_name", status: 400, message: duplicateNameError.error });
  });

  it("throw an error without a code for a response that isn't the api's", async () => {
    server.use(http.post(ATTACH_URL, () => new HttpResponse("<html>", { status: 502, statusText: "Bad Gateway" })));
    const error = await attachApiKey(session, apiKeys, { keyId: "x" }).catch((e: unknown) => e);
    expect(error).toMatchObject({ code: null, status: 502, statusText: "Bad Gateway", message: "Bad Gateway" });
  });
});
