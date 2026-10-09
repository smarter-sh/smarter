import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API_URL, SECRET_MANIFEST, applyResult, sessionContext } from "@/mocks/fixtures";
import { applyErrorHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import DropZone from "@/components/DropZone/Component";

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

  it("rejects a file that isn't a YAML mapping", async () => {
    render(<DropZone sessionContext={sessionContext} />);
    await userEvent.upload(screen.getByLabelText("Manifest file"), manifestFile("just some text\n"));
    expect(await screen.findByRole("dialog", { name: "Manifest Apply Failed" })).toHaveTextContent(
      "Manifest is not a valid object",
    );
  });

  it("opens the file dialog", async () => {
    const click = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => {});
    render(<DropZone sessionContext={sessionContext} />);
    await userEvent.click(screen.getByRole("button", { name: "File Open" }));
    expect(click).toHaveBeenCalled();
  });

  it("does nothing without a file", () => {
    render(<DropZone sessionContext={sessionContext} />);
    fireEvent.change(screen.getByLabelText("Manifest file"), { target: { files: [] } });
    fireEvent.drop(screen.getByText("Drop Zone"), { dataTransfer: { files: [] } });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("highlights the drop zone while a file is dragged over the window", () => {
    render(<DropZone sessionContext={sessionContext} />);
    // eslint-disable-next-line testing-library/no-node-access -- the highlight is a css class of the drop zone, which has no role.
    const zone = screen.getByText("Drop Zone").parentElement!;
    fireEvent.dragOver(screen.getByText("Drop Zone"));
    fireEvent.dragOver(window);
    expect(zone).toHaveClass("drop-zone--hover");

    // leaving one element for another, within the window. jsdom has no DragEvent, which is a MouseEvent.
    fireEvent(window, new MouseEvent("dragleave", { clientX: 10, clientY: 10 }));
    expect(zone).toHaveClass("drop-zone--hover");

    // leaving the window.
    fireEvent(window, new MouseEvent("dragleave", { clientX: 0, clientY: 0 }));
    expect(zone).not.toHaveClass("drop-zone--hover");

    fireEvent.dragOver(window);
    fireEvent.drop(window);
    expect(zone).not.toHaveClass("drop-zone--hover");
  });
});
