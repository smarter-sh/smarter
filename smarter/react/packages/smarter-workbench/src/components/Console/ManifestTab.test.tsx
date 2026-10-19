import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ManifestTab from "@/components/Console/ManifestTab";
import { LLMCLIENT_LIST_URL, MANIFEST_YAML, workbench } from "@/mocks/fixtures";
import { tabErrorHandlers, tabHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

vi.mock("@smarter/manifest-editor", async () => await import("@/mocks/ManifestEditor"));

describe("ManifestTab", () => {
  it("fetches the manifest, and edits it with the cli api's urls", async () => {
    server.use(...tabHandlers);
    render(<ManifestTab workbench={workbench} />);
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(await screen.findByLabelText("Manifest YAML")).toHaveValue(MANIFEST_YAML);
  });

  it("leaves for the LLM Clients list when the editor deletes the LLMClient", async () => {
    server.use(...tabHandlers);
    const user = userEvent.setup();
    render(<ManifestTab workbench={workbench} onSaved={vi.fn()} />);
    const remove = await screen.findByRole("button", { name: "Delete" });
    // jsdom can't navigate. Stub it only now: test/setup.ts resolves fetch()'s urls with location.
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });
    try {
      await user.click(remove);
      expect(assign).toHaveBeenCalledWith(LLMCLIENT_LIST_URL);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("saves without a parent that listens", async () => {
    server.use(...tabHandlers);
    const user = userEvent.setup();
    render(<ManifestTab workbench={workbench} />);
    await user.click(await screen.findByRole("button", { name: "Save" }));
    expect(screen.getByLabelText("Manifest YAML")).toBeInTheDocument();
  });

  it("says why the manifest couldn't load", async () => {
    server.use(...tabErrorHandlers);
    render(<ManifestTab workbench={workbench} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This tab couldn't load. Reload the page to try again. The request failed: 500 Internal Server Error",
    );
  });
});
