import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API_URL, SECRET_MANIFEST, applyResult, sessionContext } from "@/mocks/fixtures";
import { applyErrorHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import DropZone from "./Component";

const manifestFile = (content = SECRET_MANIFEST) => new File([content], "manifest.yaml", { type: "application/yaml" });

describe("DropZone", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("applies a chosen manifest, as json, and shows the result", async () => {
    let applied: unknown;
    server.use(
      http.post(API_URL, async ({ request }) => {
        applied = await request.json();
        return HttpResponse.json(applyResult);
      }),
    );
    render(<DropZone sessionContext={sessionContext} />);

    await userEvent.upload(screen.getByLabelText("Manifest file"), manifestFile());

    const dialog = await screen.findByRole("dialog", { name: "Manifest Applied" });
    expect(dialog).toHaveTextContent("Secret example_secret applied successfully");
    expect(dialog).toHaveTextContent("Version: 1.0.0");
    expect(applied).toMatchObject({
      apiVersion: "smarter.sh/v1",
      kind: "Secret",
      metadata: { name: "example_secret" },
    });

    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("applies a dropped manifest", async () => {
    server.use(http.post(API_URL, () => HttpResponse.json(applyResult)));
    render(<DropZone sessionContext={sessionContext} />);

    fireEvent.drop(screen.getByText("Drop Zone"), { dataTransfer: { files: [manifestFile()] } });

    expect(await screen.findByRole("dialog", { name: "Manifest Applied" })).toBeInTheDocument();
  });

  it.each([
    ["metadata.name", "apiVersion: smarter.sh/v1\nkind: Secret\nmetadata: {}\n", "Missing metadata.name"],
    ["apiVersion", "kind: Secret\nmetadata:\n  name: x\n", "Missing apiVersion"],
    ["a Smarter apiVersion", "apiVersion: v1\nkind: Secret\nmetadata:\n  name: x\n", "Invalid apiVersion"],
    ["kind", "apiVersion: smarter.sh/v1\nmetadata:\n  name: x\n", "Missing kind"],
  ])("rejects a manifest without %s, without applying it", async (_, content, message) => {
    // an apply request would be unhandled, and fail the test.
    render(<DropZone sessionContext={sessionContext} />);
    await userEvent.upload(screen.getByLabelText("Manifest file"), manifestFile(content));
    expect(await screen.findByRole("dialog", { name: "Manifest Apply Failed" })).toHaveTextContent(message);
  });

  it("shows the api's rejection", async () => {
    server.use(...applyErrorHandlers);
    render(<DropZone sessionContext={sessionContext} />);
    await userEvent.upload(screen.getByLabelText("Manifest file"), manifestFile());
    expect(await screen.findByRole("dialog", { name: "Manifest Apply Failed" })).toHaveTextContent(
      "Manifest apply failed (400)",
    );
  });
});
