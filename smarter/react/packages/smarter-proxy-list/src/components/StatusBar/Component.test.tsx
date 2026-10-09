import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeObject } from "@/mocks/fixtures";

import { StatusBar } from "./Component";

describe("StatusBar", () => {
  it("shows an active Proxy with an API key and restricted paths", () => {
    render(<StatusBar proxy={makeObject(1, { allowedPaths: ["/v1/chat/completions"] })} />);
    expect(screen.getByTitle("Active: the Proxy forwards requests.")).toBeInTheDocument();
    expect(
      screen.getByTitle("API key: Secret openai_api_key (provider's), sent in Authorization."),
    ).toBeInTheDocument();
    expect(screen.getByTitle("Allowed paths: /v1/chat/completions")).toHaveTextContent("1 path");
  });

  it("shows an inactive Proxy without an API key, that allows every path", () => {
    render(<StatusBar proxy={makeObject(1, { isActive: false, apiKeySecretName: null as never })} />);
    expect(screen.getByTitle("Inactive: the Proxy refuses every request.")).toBeInTheDocument();
    expect(screen.getByTitle(/^No API key:/)).toBeInTheDocument();
    expect(screen.getByTitle(/^All paths are allowed:/)).toHaveTextContent("All paths");
  });
});
