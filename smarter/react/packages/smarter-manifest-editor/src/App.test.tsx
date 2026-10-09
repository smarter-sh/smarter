import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { APPLY_API_URL, SECRET_IN_USE_YAML, VALIDATE_API_URL, appProps } from "@/mocks/fixtures";
import { cliHandlers, invalidHandler, validHandler } from "@/mocks/handlers";
import { server } from "@test/server";

import App from "./App";

vi.mock("@monaco-editor/react", async () => await import("@/mocks/MonacoEditor"));

const VALIDATION = { timeout: 3000 };

function edit(yaml: string) {
  fireEvent.change(screen.getByLabelText("Manifest YAML"), { target: { value: yaml } });
}

describe("App", () => {
  beforeEach(() => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
  });

  it("validates the manifest, and lists its problems", async () => {
    server.use(invalidHandler);
    render(<App {...appProps} />);
    expect(await screen.findByText("1 problem", {}, VALIDATION)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /spec.config.value: value must be at least 32 characters/ }),
    ).toBeInTheDocument();
  });

  it("finds a syntax error without asking the api", async () => {
    server.use(validHandler);
    render(<App {...appProps} />);
    await screen.findByText("No problems", {}, VALIDATION);
    edit("kind: [unclosed");
    expect(await screen.findByText("1 problem", {}, VALIDATION)).toBeInTheDocument();
  });

  it("saves the edited manifest, without its status", async () => {
    let applied: Record<string, unknown> | undefined;
    server.use(
      http.post(APPLY_API_URL, async ({ request }) => {
        applied = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ message: "Secret example_secret applied" });
      }),
      ...cliHandlers,
    );
    const user = userEvent.setup();
    render(<App {...appProps} />);
    const save = screen.getByRole("button", { name: /^Save:/ });
    expect(save).toBeDisabled();

    edit(appProps.initialManifest.replace("An example secret.", "An edited secret."));
    await screen.findByText("No problems", {}, VALIDATION);
    await user.click(screen.getByRole("button", { name: "Save: Apply your changes to this manifest" }));

    expect(await screen.findByRole("dialog", { name: "Saved" })).toHaveTextContent("Secret example_secret applied");
    expect(applied).toMatchObject({ kind: "Secret", metadata: { description: "An edited secret." } });
    expect(applied).not.toHaveProperty("status");
  });

  it("clones the resource with a new name", async () => {
    let cloned: { metadata?: { name?: string } } | undefined;
    server.use(
      http.post(APPLY_API_URL, async ({ request }) => {
        cloned = (await request.json()) as typeof cloned;
        return HttpResponse.json({});
      }),
      ...cliHandlers,
    );
    const user = userEvent.setup();
    render(<App {...appProps} />);

    await user.click(screen.getByRole("button", { name: /^Clone:/ }));
    await user.type(screen.getByRole("textbox", { name: "New Secret name" }), "secret_copy");
    await user.click(screen.getByRole("button", { name: "OK" }));

    expect(await screen.findByRole("dialog", { name: "Cloned" })).toHaveTextContent("Secret secret_copy created");
    expect(cloned?.metadata?.name).toBe("secret_copy");
  });

  it("deletes the resource, by kind and name", async () => {
    let deleted = "";
    server.use(
      http.post("/api/v1/cli/delete/:kind/", ({ params, request }) => {
        deleted = `${params.kind} ${new URL(request.url).searchParams.get("name")}`;
        return HttpResponse.json({});
      }),
      ...cliHandlers,
    );
    const user = userEvent.setup();
    render(<App {...appProps} />);

    await user.click(screen.getByRole("button", { name: "Delete: Delete this Secret" }));
    await user.click(screen.getByRole("button", { name: "OK" }));

    expect(await screen.findByRole("dialog", { name: "Deleted" })).toBeInTheDocument();
    expect(deleted).toBe("Secret example_secret");
  });

  it("does not delete a resource that others depend on", async () => {
    server.use(...cliHandlers);
    render(<App {...appProps} initialManifest={SECRET_IN_USE_YAML} />);
    expect(screen.getByRole("button", { name: /LLMClient example_llmclient/ })).toBeDisabled();
  });
});

describe("App, when things go wrong", () => {
  beforeEach(() => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
  });

  it("lets the user save when the api can't validate, and reports what's wrong", async () => {
    server.use(
      http.post(VALIDATE_API_URL, () => HttpResponse.error()),
      ...cliHandlers,
    );
    const user = userEvent.setup();
    render(<App {...appProps} />);
    edit("just: a mapping\n");
    await screen.findByText("No problems", {}, VALIDATION);
    await user.click(screen.getByRole("button", { name: /^Save:/ }));
    expect(await screen.findByRole("dialog", { name: "Save Failed" })).toHaveTextContent("apiVersion is missing");
  });

  it("validates YAML that isn't a mapping", async () => {
    let validated: unknown;
    server.use(
      http.post(VALIDATE_API_URL, async ({ request }) => {
        validated = await request.json();
        return HttpResponse.json({ data: { valid: false, errors: [{ loc: [], message: "not a manifest" }] } });
      }),
    );
    render(<App {...appProps} />);
    edit("just a string\n");
    expect(await screen.findByText("1 problem", {}, VALIDATION)).toBeInTheDocument();
    expect(validated).toBe("just a string");
  });

  it("reports the api's error when a save fails", async () => {
    server.use(
      http.post(APPLY_API_URL, () => HttpResponse.json({ error: "Secret is invalid" }, { status: 400 })),
      ...cliHandlers,
    );
    const user = userEvent.setup();
    render(<App {...appProps} />);
    edit(appProps.initialManifest.replace("An example secret.", "An edited secret."));
    await screen.findByText("No problems", {}, VALIDATION);
    await user.click(screen.getByRole("button", { name: /^Save:/ }));
    const dialog = await screen.findByRole("dialog", { name: "Save Failed" });
    expect(dialog).toHaveTextContent("Secret is invalid");
    await user.click(within(dialog).getAllByRole("button")[0]);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    // the changes are still unsaved.
    expect(screen.getByRole("button", { name: /^Revert:/ })).toBeEnabled();
  });

  it("reports a network error as a failure", async () => {
    server.use(
      http.post(APPLY_API_URL, () => HttpResponse.error()),
      ...cliHandlers,
    );
    const user = userEvent.setup();
    render(<App {...appProps} />);
    edit(appProps.initialManifest.replace("An example secret.", "An edited secret."));
    await screen.findByText("No problems", {}, VALIDATION);
    await user.click(screen.getByRole("button", { name: /^Save:/ }));
    expect(await screen.findByRole("dialog", { name: "Save Failed" })).toBeInTheDocument();
  });

  it("reverts the user's changes", async () => {
    server.use(...cliHandlers);
    const user = userEvent.setup();
    render(<App {...appProps} />);
    edit(appProps.initialManifest.replace("An example secret.", "An edited secret."));
    await user.click(screen.getByRole("button", { name: /^Revert:/ }));
    expect(screen.getByLabelText("Manifest YAML")).toHaveValue(appProps.initialManifest);
    expect(screen.getByRole("button", { name: /^Revert:/ })).toBeDisabled();
  });

  it("doesn't clone without a new name, or when the user cancels", async () => {
    let calls = 0;
    server.use(
      http.post(APPLY_API_URL, () => {
        calls += 1;
        return HttpResponse.json({});
      }),
      ...cliHandlers,
    );
    const user = userEvent.setup();
    render(<App {...appProps} />);
    await user.click(screen.getByRole("button", { name: /^Clone:/ }));
    await user.click(screen.getByRole("button", { name: "OK" }));
    await user.click(screen.getByRole("button", { name: /^Clone:/ }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(calls).toBe(0);
  });

  it("reports a clone that fails", async () => {
    server.use(
      http.post(APPLY_API_URL, () => HttpResponse.json({ error: { description: "name taken" } }, { status: 409 })),
      ...cliHandlers,
    );
    const user = userEvent.setup();
    render(<App {...appProps} />);
    await user.click(screen.getByRole("button", { name: /^Clone:/ }));
    await user.type(screen.getByRole("textbox", { name: "New Secret name" }), "taken");
    await user.click(screen.getByRole("button", { name: "OK" }));
    expect(await screen.findByRole("dialog", { name: "Clone Failed" })).toHaveTextContent("name taken");
  });

  it("warns that a delete loses unsaved changes, and deletes nothing when the user cancels", async () => {
    server.use(...cliHandlers);
    const user = userEvent.setup();
    render(<App {...appProps} />);
    edit(appProps.initialManifest.replace("An example secret.", "An edited secret."));
    await user.click(screen.getByRole("button", { name: "Delete: Delete this Secret" }));
    expect(screen.getByRole("dialog", { name: "Delete Secret" })).toHaveTextContent(
      "Your unsaved changes will be lost.",
    );
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("reports a delete that fails", async () => {
    server.use(
      http.post("/api/v1/cli/delete/:kind/", () => HttpResponse.json({ error: "in use" }, { status: 400 })),
      ...cliHandlers,
    );
    const user = userEvent.setup();
    render(<App {...appProps} />);
    await user.click(screen.getByRole("button", { name: "Delete: Delete this Secret" }));
    await user.click(screen.getByRole("button", { name: "OK" }));
    expect(await screen.findByRole("dialog", { name: "Delete Failed" })).toHaveTextContent("in use");
  });

  it.each([
    ["the page the user came from", "http://localhost:9357/secrets/", "http://localhost:9357/secrets/"],
    ["the dashboard, without a referrer", "", "/dashboard/"],
    ["the dashboard, from another site", "https://example.com/", "/dashboard/"],
  ])("leaves a deleted resource's page for %s", async (_, referrer, destination) => {
    const assign = vi.fn();
    vi.spyOn(document, "referrer", "get").mockReturnValue(referrer);
    server.use(...cliHandlers);
    const user = userEvent.setup();
    render(<App {...appProps} />);
    await user.click(screen.getByRole("button", { name: "Delete: Delete this Secret" }));
    await user.click(screen.getByRole("button", { name: "OK" }));
    const dialog = await screen.findByRole("dialog", { name: "Deleted" });
    // jsdom can't navigate. Stub it only now: test/setup.ts resolves fetch()'s urls with location.
    vi.stubGlobal("location", { origin: window.location.origin, pathname: "/manifest/", assign });
    try {
      await user.click(within(dialog).getAllByRole("button")[0]);
      expect(assign).toHaveBeenCalledWith(destination);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("can't clone or delete a manifest that it can't parse", () => {
    server.use(...cliHandlers);
    render(<App {...appProps} initialManifest={"kind: [unclosed"} />);
    expect(screen.getByRole("button", { name: "Delete: Delete this resource" })).toBeDisabled();
    expect(screen.getByRole("button", { name: /^Download: Save this manifest as manifest.yaml/ })).toBeInTheDocument();
  });
});
