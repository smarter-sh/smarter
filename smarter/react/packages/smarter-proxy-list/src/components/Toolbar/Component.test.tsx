import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { ACTIONS_URL as BASE, makeObject, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import { Toolbar } from "@/components/Toolbar/Component";

function renderToolbar(proxy = makeObject(1, { name: "first_example" })) {
  const onRequery = vi.fn();
  render(<Toolbar sessionContext={sessionContext} proxy={proxy} onRequery={onRequery} />);
  return { onRequery, user: userEvent.setup() };
}

describe("Toolbar", () => {
  it("links to the manifest", () => {
    renderToolbar();
    expect(screen.getByRole("link", { name: /^(Edit|Manifest):/ })).toHaveAttribute("href", makeObject(1).manifestUrl);
  });

  it("deletes, then queries the list again", async () => {
    server.use(...actionHandlers);
    const { onRequery, user } = renderToolbar();

    await user.click(screen.getByRole("button", { name: /^Delete:/ }));
    expect(screen.getByRole("dialog", { name: "Delete Proxy" })).toHaveTextContent("first_example");
    await user.click(screen.getByRole("button", { name: "OK" }));

    expect(await screen.findByRole("dialog", { name: /Success/ })).toHaveTextContent("Successfully deleted proxy");
    await user.click(screen.getAllByRole("button", { name: "Close" })[0]);
    expect(onRequery).toHaveBeenCalledOnce();
  });

  it("does nothing when deleting is cancelled", async () => {
    const { onRequery, user } = renderToolbar();
    await user.click(screen.getByRole("button", { name: /^Delete:/ }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(onRequery).not.toHaveBeenCalled();
  });

  it("renames, with the new name in the url", async () => {
    let renamedTo = "";
    server.use(
      http.post(`${BASE}rename/:id/:newName/`, ({ params }) => {
        renamedTo = String(params.newName);
        return HttpResponse.json(makeObject(1, { name: renamedTo }));
      }),
    );
    const { user } = renderToolbar();

    await user.click(screen.getByRole("button", { name: /^Rename:/ }));
    const input = screen.getByPlaceholderText("Enter new proxy name");
    expect(input).toHaveValue("first_example");
    await user.clear(input);
    await user.type(input, "renamed_example");
    await user.click(screen.getByRole("button", { name: "OK" }));

    expect(await screen.findByRole("dialog", { name: /Success/ })).toHaveTextContent("renamed_example");
    expect(renamedTo).toBe("renamed_example");
  });

  it("shows the server's error message when an action fails", async () => {
    server.use(
      http.post(`${BASE}clone/:id/:newName/`, () =>
        HttpResponse.json({ error: "The name copy is already used." }, { status: 400 }),
      ),
    );
    const { onRequery, user } = renderToolbar();

    await user.click(screen.getByRole("button", { name: /^Clone:/ }));
    await user.type(screen.getByPlaceholderText("Enter new proxy name"), "copy");
    await user.click(screen.getByRole("button", { name: "OK" }));

    expect(await screen.findByRole("dialog", { name: /Error/ })).toHaveTextContent("The name copy is already used.");
    expect(onRequery).not.toHaveBeenCalled();
  });

  it("disables deleting one that cannot be deleted", () => {
    renderToolbar(makeObject(3, { canDelete: false }));
    expect(screen.getByRole("button", { name: /You can't delete this proxy/ })).toBeDisabled();
  });

  it("copies the Proxy's url, and shows that it did", async () => {
    const { user } = renderToolbar();
    const copy = screen.getByRole("button", { name: /^Copy URL:/ });
    await user.click(copy);
    expect(await navigator.clipboard.readText()).toBe("http://localhost:9357/api/v1/proxy/example-1/");
    // eslint-disable-next-line testing-library/no-node-access -- the button shows that it copied with its icon.
    expect(copy.querySelector("i")).toHaveClass("bi-clipboard-check");
  });

  it("says when it can't copy the url", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const { user } = renderToolbar();
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new Error("denied"));
    await user.click(screen.getByRole("button", { name: /^Copy URL:/ }));
    expect(await screen.findByRole("dialog", { name: /Error/ })).toHaveTextContent(
      "Could not copy the URL to the clipboard: http://localhost:9357/api/v1/proxy/example-1/",
    );
  });

  it("can't copy the url of a Proxy whose endpoints are disabled", () => {
    renderToolbar(makeObject(1, { url: "" }));
    expect(screen.getByRole("button", { name: /^The proxy endpoints are disabled/ })).toBeDisabled();
  });

  it("starts renaming a Proxy without a name from an empty name", async () => {
    const { user } = renderToolbar(makeObject(1, { name: "" }));
    await user.click(screen.getByRole("button", { name: /^Rename:/ }));
    expect(screen.getByPlaceholderText(/new/i)).toHaveValue("");
  });

  it("shows the status of a failed action without an error message", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.post(`${BASE}delete/:id/`, () => new HttpResponse("oops", { status: 500, statusText: "Oops" })));
    const { user } = renderToolbar();
    await user.click(screen.getByRole("button", { name: /^Delete:/ }));
    await user.click(screen.getByRole("button", { name: "OK" }));
    expect(await screen.findByRole("dialog", { name: /Error/ })).toHaveTextContent(
      "Failed to delete proxy (500): Oops",
    );
  });
});
