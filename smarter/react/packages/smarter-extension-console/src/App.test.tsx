import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "@/App";
import { detailContext, listContext } from "@/mocks/fixtures";
import { detailHandlers, listHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

describe("App", () => {
  it("renders the Extensions list on the list page", async () => {
    server.use(...listHandlers());
    render(<App context={listContext} />);
    expect(await screen.findByRole("tab", { name: /Installed/ })).toBeInTheDocument();
  });

  it("renders an extension's page on its page", async () => {
    server.use(...detailHandlers());
    render(<App context={detailContext} />);
    expect(await screen.findByRole("heading", { level: 1, name: "Weather" })).toBeInTheDocument();
  });
});
