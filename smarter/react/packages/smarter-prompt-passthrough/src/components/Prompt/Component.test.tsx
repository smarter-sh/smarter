import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { API_URL, PROVIDER_API_URL, completion, sessionContext } from "@/mocks/fixtures";
import { passthroughErrorHandlers, providerHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import Prompt from "./Component";

vi.mock("@monaco-editor/react", async () => await import("@/mocks/MonacoEditor"));

function setup() {
  render(
    <Prompt
      sessionContext={sessionContext}
      defaultLLMProviderId={1}
      defaultTemplateId={1}
      providerApiUrl={PROVIDER_API_URL}
    />,
  );
  return userEvent.setup();
}

const requestJson = () => JSON.parse((screen.getByLabelText("Request JSON") as HTMLTextAreaElement).value);

describe("Prompt", () => {
  it("selects the default provider, and its model, in the request", async () => {
    server.use(...providerHandlers);
    setup();

    expect(await screen.findByRole("option", { name: "anthropic" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "LLM provider" })).toHaveValue("1");
    expect(requestJson()).toMatchObject({ model: "gpt-4o-mini", messages: [{ role: "user", content: "Hello world" }] });
  });

  it("changes the request's model with the provider, and its body with the template", async () => {
    server.use(...providerHandlers);
    const user = setup();
    await screen.findByRole("option", { name: "anthropic" });

    await user.selectOptions(screen.getByRole("combobox", { name: "LLM provider" }), "anthropic");
    expect(requestJson().model).toBe("claude-haiku-4-5");

    const template = screen.getByRole("combobox", { name: "Prompt template" });
    await user.selectOptions(template, screen.getAllByRole("option", { name: /./ }).at(-1)!.textContent!);
    expect(requestJson().model).toBe("claude-haiku-4-5");
  });

  it("sends the request to the selected provider, and shows the response", async () => {
    let sent: { provider: string; body: unknown } | undefined;
    server.use(
      ...providerHandlers,
      http.post(`${API_URL}:provider/`, async ({ params, request }) => {
        sent = { provider: String(params.provider), body: await request.json() };
        return HttpResponse.json(completion);
      }),
    );
    const user = setup();
    await screen.findByRole("option", { name: "anthropic" });

    await user.click(screen.getByRole("button", { name: "SEND" }));

    expect(await screen.findByRole("tab", { name: "Response", selected: true })).toBeInTheDocument();
    expect(screen.getByText(/Hello! How can I help\?/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /\(200\)/ })).toBeInTheDocument();
    expect(sent).toMatchObject({ provider: "openai", body: { model: "gpt-4o-mini" } });
  });

  it("shows the provider's error response", async () => {
    server.use(...passthroughErrorHandlers);
    const user = setup();
    await screen.findByRole("option", { name: "anthropic" });

    await user.click(screen.getByRole("button", { name: "SEND" }));

    expect(await screen.findByRole("heading", { name: /\(401\)/ })).toBeInTheDocument();
    expect(screen.getByText(/Invalid API key/)).toBeInTheDocument();
  });
});
