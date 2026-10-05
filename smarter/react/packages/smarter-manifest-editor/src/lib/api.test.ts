import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { sessionContext } from "@/mocks/fixtures";
import { server } from "@test/server";

import { callCli } from "./api";

const URL = "/api/v1/cli/apply/";

describe("callCli", () => {
  it("returns the api's message, else the success message", async () => {
    server.use(http.post(URL, () => HttpResponse.json({ message: "applied" })));
    expect(await callCli(sessionContext, URL, {}, "saved")).toEqual({ ok: true, message: "applied" });
    server.use(http.post(URL, () => HttpResponse.json({})));
    expect(await callCli(sessionContext, URL, {}, "saved")).toEqual({ ok: true, message: "saved" });
  });

  it.each([
    ["a string", { error: "Bad manifest" }, "Bad manifest"],
    ["a description", { error: { description: "Invalid spec" } }, "Invalid spec"],
    ["a message", { error: { message: "Not found" } }, "Not found"],
  ])("returns the api's error, as %s", async (_, body, message) => {
    server.use(http.post(URL, () => HttpResponse.json(body, { status: 400 })));
    expect(await callCli(sessionContext, URL, {}, "saved")).toEqual({ ok: false, message });
  });

  it("returns the status of an error without a body", async () => {
    server.use(http.post(URL, () => new HttpResponse(null, { status: 502, statusText: "Bad Gateway" })));
    expect(await callCli(sessionContext, URL, {}, "saved")).toEqual({ ok: false, message: "502 Bad Gateway" });
  });
});
