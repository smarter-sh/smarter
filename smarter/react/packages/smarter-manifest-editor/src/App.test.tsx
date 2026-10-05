import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { APPLY_API_URL, SECRET_IN_USE_YAML, appProps } from "@/mocks/fixtures";
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
