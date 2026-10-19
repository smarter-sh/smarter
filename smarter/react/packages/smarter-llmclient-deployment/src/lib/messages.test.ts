import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api";
import { errorMessage, successMessage } from "@/lib/messages";
import type { ErrorCode } from "@/lib/types";

describe("successMessage", () => {
  it("says what each action did", () => {
    expect(successMessage({ action: "create", name: "k", attached: true })).toBe(
      "k is created, and attached. Every request to the LLMClient's url now needs it.",
    );
    expect(successMessage({ action: "create", name: "k", attached: false })).toBe("k is created.");
    expect(successMessage({ action: "attach", name: "k" })).toBe(
      "k is attached. Every request to the LLMClient's url now needs it.",
    );
    expect(successMessage({ action: "detach" })).toBe("The api key is detached. The LLMClient's url is public again.");
  });
});

describe("errorMessage", () => {
  const apiError = (code: ErrorCode | null, status = 400, statusText = "Bad Request") =>
    new ApiError("English", code, status, statusText);

  it("explains each of the api's codes", () => {
    const codes: ErrorCode[] = [
      "not_owner",
      "not_admin",
      "not_account_admin",
      "invalid_name",
      "api_key_not_found",
      "not_found",
      "invalid_request",
    ];
    const messages = codes.map((code) => errorMessage(apiError(code)));
    expect(new Set(messages).size).toBe(codes.length);
    expect(messages.some((message) => message === "English")).toBe(false);
    expect(errorMessage(apiError("duplicate_name"), "my_key")).toBe("You already have an api key named my_key.");
  });

  it("says how a request failed that isn't the api's error", () => {
    expect(errorMessage(apiError(null, 502, "Bad Gateway"))).toBe("The request failed: 502 Bad Gateway");
    expect(errorMessage(new TypeError("Failed to fetch"))).toBe("The request failed: Failed to fetch");
    expect(errorMessage("offline")).toBe("The request failed: offline");
  });
});
