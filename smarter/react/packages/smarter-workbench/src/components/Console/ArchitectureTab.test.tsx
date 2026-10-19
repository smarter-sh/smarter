import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { leafTree, stackademyTree } from "@smarter/llmclient-architecture/mocks";

import ArchitectureTab from "@/components/Console/ArchitectureTab";
import { ARCHITECTURE_URL, workbench } from "@/mocks/fixtures";
import { tabErrorHandlers, tabHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

describe("ArchitectureTab", () => {
  it("fetches the LLMClient's tree, and draws it", async () => {
    server.use(...tabHandlers);
    render(<ArchitectureTab workbench={workbench} />);
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "How this LLMClient is built" })).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "LLMClient stackademy_sql" })).toBeInTheDocument();
  });

  it("fetches the tree again when it is reloaded", async () => {
    let requests = 0;
    server.use(
      http.get(ARCHITECTURE_URL, () => {
        requests += 1;
        return HttpResponse.json(requests === 1 ? stackademyTree : leafTree);
      }),
    );
    const user = userEvent.setup();
    render(<ArchitectureTab workbench={workbench} />);
    expect(await screen.findByRole("article", { name: "SqlPlugin stackademy_sql" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reload" }));
    expect(await screen.findByRole("article", { name: "LLMClient hello_world" })).toBeInTheDocument();
    expect(requests).toBe(2);
  });

  it("says why the tree couldn't load", async () => {
    server.use(...tabErrorHandlers);
    render(<ArchitectureTab workbench={workbench} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The request failed: 404 Not Found");
  });
});
