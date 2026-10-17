import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { API_URL, PROVIDER_API_URL, completion, sessionContext } from "@/mocks/fixtures";
import { passthroughErrorHandlers, providerHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import Prompt from "@/components/Prompt/Component";

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
    expect(requestJson()).toMatchObject({
      model: "gpt-4o-mini",
      messages: [
        { role: "user", content: "Hello world" },
        { role: "assistant", content: "Hello! How can I help?" },
        { role: "user", content: "What's the weather in San Francisco?" },
      ],
    });
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
    expect(await screen.findByRole("region", { name: "Reply" })).toHaveTextContent("Hello! How can I help?");
    expect(screen.getByText(/^200/)).toHaveClass("badge-light-success");
    expect(screen.getByLabelText("Response JSON")).toHaveValue(JSON.stringify(completion, null, 2));
    expect(sent).toMatchObject({ provider: "openai", body: { model: "gpt-4o-mini" } });
  });

  it("shows the spinner on the response tab while the request is on its way", async () => {
    let respond: () => void = () => {};
    server.use(
      ...providerHandlers,
      http.post(`${API_URL}:provider/`, async () => {
        await new Promise<void>((resolve) => (respond = resolve));
        return HttpResponse.json(completion);
      }),
    );
    const user = setup();
    await screen.findByRole("option", { name: "anthropic" });

    await user.click(screen.getByRole("button", { name: "SEND" }));

    expect(screen.getByRole("tab", { name: "Response", selected: true })).toBeInTheDocument();
    expect(await screen.findByText("Waiting for the provider's response…")).toBeInTheDocument();
    respond();
    expect(await screen.findByRole("region", { name: "Reply" })).toBeInTheDocument();
  });

  it("shows a response that isn't JSON as it is", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    server.use(
      ...providerHandlers,
      http.post(`${API_URL}:provider/`, () => new HttpResponse("<h1>Bad Gateway</h1>", { status: 502 })),
    );
    const user = setup();
    await screen.findByRole("option", { name: "anthropic" });

    await user.click(screen.getByRole("button", { name: "SEND" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The response isn't JSON.");
    expect(screen.getByLabelText("Response JSON")).toHaveValue("<h1>Bad Gateway</h1>");
  });

  it("shows a request that got no response as a network error", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(
      ...providerHandlers,
      http.post(`${API_URL}:provider/`, () => HttpResponse.error()),
    );
    const user = setup();
    await screen.findByRole("option", { name: "anthropic" });

    await user.click(screen.getByRole("button", { name: "SEND" }));

    expect(await screen.findByText("Network error")).toHaveClass("badge-light-danger");
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("shows the provider's error response", async () => {
    server.use(...passthroughErrorHandlers);
    const user = setup();
    await screen.findByRole("option", { name: "anthropic" });

    await user.click(screen.getByRole("button", { name: "SEND" }));

    expect(await screen.findByText(/^401/)).toHaveClass("badge-light-danger");
    expect(screen.getByRole("alert")).toHaveTextContent("Invalid API key");
  });

  it("sends the request as the user edits it, and returns to the request", async () => {
    let sent: unknown;
    server.use(
      ...providerHandlers,
      http.post(`${API_URL}:provider/`, async ({ request }) => {
        sent = await request.text();
        return HttpResponse.json(completion);
      }),
    );
    const user = setup();
    await screen.findByRole("option", { name: "anthropic" });

    fireEvent.change(screen.getByLabelText("Request JSON"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Request JSON"), { target: { value: '{"edited": true}' } });
    await user.click(screen.getByRole("button", { name: "SEND" }));
    await screen.findByRole("tab", { name: "Response", selected: true });
    expect(sent).toBe('{"edited": true}');

    await user.click(screen.getByRole("tab", { name: "Request" }));
    expect(screen.getByRole("tab", { name: "Request", selected: true })).toBeInTheDocument();
    expect(screen.getByLabelText("Request JSON")).toHaveValue('{"edited": true}');
  });

  it("leaves the request empty when there are no providers", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    server.use(http.post(PROVIDER_API_URL, () => HttpResponse.json({ providers: [] })));
    setup();
    await vi.waitFor(() => expect(warn).toHaveBeenCalledWith(expect.anything(), "No LLM providers found from API"));
    expect(screen.getByLabelText("Request JSON")).toHaveValue("");
  });

  it("logs a failure to load the providers", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.post(PROVIDER_API_URL, () => HttpResponse.error()));
    setup();
    await vi.waitFor(() =>
      expect(error).toHaveBeenCalledWith(expect.anything(), "Error fetching LLM providers:", expect.any(Error)),
    );
  });

  it("uses the first template and provider without defaults", async () => {
    server.use(...providerHandlers);
    render(
      <Prompt
        sessionContext={sessionContext}
        defaultLLMProviderId={undefined as never}
        defaultTemplateId={undefined as never}
        providerApiUrl={PROVIDER_API_URL}
      />,
    );
    await screen.findByRole("option", { name: "anthropic" });
    expect(requestJson()).toMatchObject({ model: "gpt-4o-mini" });
  });
});
