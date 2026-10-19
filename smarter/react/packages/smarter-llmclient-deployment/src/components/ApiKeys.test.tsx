import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import ApiKeys from "@/components/ApiKeys";
import type { LLMClientDeploymentPage } from "@/lib/types";
import {
  CREATE_URL,
  SECRET,
  attachedResponse,
  createdResponse,
  duplicateNameError,
  firstApiKey,
  inactiveKeyPage,
  makeApiKeys,
  secondApiKey,
  session,
  sharedPage,
  workbenchPage,
  authenticatedPage,
} from "@/mocks/fixtures";
import { actionHandlers, errorHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

const COMMAND = "python manage.py create_api_key";
const API_KEYS_URL = "https://platform.example.com/api-keys/";

function showApiKeys(page: LLMClientDeploymentPage = workbenchPage, onPage = vi.fn()) {
  render(
    <ApiKeys
      apiKeys={page.apiKeys!}
      createApiKeyCommand={COMMAND}
      apiKeysUrl={API_KEYS_URL}
      session={session}
      onPage={onPage}
    />,
  );
  return onPage;
}

const row = (name: string) => screen.getByRole("row", { name: new RegExp(name) });

describe("ApiKeys", () => {
  it("lists the account's api keys, and says that the url is public", () => {
    showApiKeys();
    expect(screen.getByText("No api key is attached: the url is public.")).toBeInTheDocument();
    expect(within(row(firstApiKey.name)).getByText("On")).toBeInTheDocument();
    expect(within(row(firstApiKey.name)).getByText(firstApiKey.description)).toBeInTheDocument();
    expect(within(row(secondApiKey.name)).getByText("Off")).toBeInTheDocument();
    expect(within(row(secondApiKey.name)).getByText("Never")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Detach" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "API Keys" })).toHaveAttribute("target", "_top");
  });

  it("says which key every request needs", () => {
    showApiKeys(authenticatedPage);
    expect(screen.getByText(/Every request to the url needs/)).toHaveTextContent(firstApiKey.name);
    expect(within(row(firstApiKey.name)).getByText("Attached")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Detach" })).toBeInTheDocument();
  });

  it("says that an attached key that is turned off leaves the url public", () => {
    showApiKeys(inactiveKeyPage);
    expect(screen.getByText(/is attached, but turned off/)).toHaveTextContent(secondApiKey.name);
  });

  it("attaches a key, and shows the page as it now is", async () => {
    server.use(...actionHandlers());
    const user = userEvent.setup();
    const onPage = showApiKeys();
    await user.click(within(row(firstApiKey.name)).getByRole("button", { name: "Attach" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "my_site_chat is attached. Every request to the LLMClient's url now needs it.",
    );
    expect(onPage).toHaveBeenCalledWith(attachedResponse.page);
  });

  it("detaches the key", async () => {
    server.use(...actionHandlers());
    const user = userEvent.setup();
    showApiKeys(authenticatedPage);
    await user.click(screen.getByRole("button", { name: "Detach" }));
    expect(await screen.findByRole("status")).toHaveTextContent("The api key is detached.");
  });

  it("creates a key, attaches it, and shows its secret once", async () => {
    let body: unknown = null;
    server.use(
      http.post(CREATE_URL, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(createdResponse);
      }),
    );
    const user = userEvent.setup();
    const onPage = showApiKeys();
    await user.type(screen.getByLabelText("Name"), "my_new_key");
    await user.type(screen.getByLabelText("Description"), "the chat");
    expect(screen.getByLabelText("Attach it to this LLMClient")).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Create the api key" }));
    expect(await screen.findByRole("status")).toHaveTextContent("my_new_key is created, and attached.");
    expect(body).toEqual({ name: "my_new_key", description: "the chat", attach: true });
    expect(screen.getByRole("heading", { name: "Copy its secret now" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "my_new_key" })).toHaveTextContent(SECRET);
    expect(onPage).toHaveBeenCalledWith(createdResponse.page);
    // the form is cleared, for another key.
    expect(screen.getByLabelText("Name")).toHaveValue("");

    // the next action hides the secret.
    server.use(...actionHandlers());
    await user.click(within(row(firstApiKey.name)).getByRole("button", { name: "Attach" }));
    await screen.findByText(/my_site_chat is attached/);
    expect(screen.queryByText(SECRET)).not.toBeInTheDocument();
  });

  it("creates a key without attaching it", async () => {
    server.use(...actionHandlers({ page: workbenchPage, newApiKey: { name: "unattached", secret: SECRET } }));
    const user = userEvent.setup();
    showApiKeys();
    await user.type(screen.getByLabelText("Name"), "unattached");
    await user.click(screen.getByLabelText("Attach it to this LLMClient"));
    await user.click(screen.getByRole("button", { name: "Create the api key" }));
    expect(await screen.findByRole("status")).toHaveTextContent(/^unattached is created\.$/);
  });

  it("explains why an action failed, and keeps the form", async () => {
    server.use(...errorHandlers(duplicateNameError));
    const user = userEvent.setup();
    const onPage = showApiKeys();
    await user.type(screen.getByLabelText("Name"), "my_site_chat");
    await user.click(screen.getByRole("button", { name: "Create the api key" }));
    expect(await screen.findByRole("status")).toHaveTextContent("You already have an api key named my_site_chat.");
    expect(screen.getByLabelText("Name")).toHaveValue("my_site_chat");
    expect(onPage).not.toHaveBeenCalled();
  });

  it("is read-only for a user who isn't an account admin", () => {
    showApiKeys(sharedPage);
    expect(screen.getByText("There are no api keys that you can manage yet.")).toBeInTheDocument();
    expect(
      screen.getByText("Only the LLMClient's owner, or an account admin, can change its api key."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create the api key" })).not.toBeInTheDocument();
    expect(screen.getByRole("group", { name: "bash" })).toHaveTextContent(COMMAND);
  });

  it("lets a staff user who may not change the LLMClient create a key, but not attach one", () => {
    showApiKeys({ ...workbenchPage, apiKeys: makeApiKeys({ canManage: false }) });
    expect(screen.getByRole("button", { name: "Create the api key" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Attach it to this LLMClient")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Attach" })).not.toBeInTheDocument();
  });
});
