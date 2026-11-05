import { describe, expect, it } from "vitest";

import { actionUrl } from "./actionUrl";
import type { SessionContext } from "./Types";

const session = (ApiUrl: string) => ({ ApiUrl }) as SessionContext;

describe("actionUrl", () => {
  it("makes the action a sibling of the list endpoint", () => {
    expect(actionUrl(session("/api/web/secret/listview/"), "delete/12/")).toBe("/api/web/secret/delete/12/");
  });

  it("accepts a list endpoint without its trailing slash", () => {
    expect(actionUrl(session("/plugin/api/listview"), "clone/1/copy/")).toBe("/plugin/api/clone/1/copy/");
  });
});
