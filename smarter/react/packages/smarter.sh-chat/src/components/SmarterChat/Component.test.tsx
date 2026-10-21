import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createRef } from "react";

import {
  CONFIG_URL,
  PROMPT_URL,
  SESSION_KEY,
  config,
  configWithCode,
  configWithDiagram,
  configWithImages,
  configWithHistory,
  configWithStyles,
  chatStyles,
  leanConfig,
  progressEvents,
  promptEventStream,
  promptMaxTokensResponse,
  promptResponse,
  props,
} from "@/mocks/fixtures";
import {
  chatHandlers,
  configErrorHandlers,
  historyHandlers,
  loadingHandlers,
  promptErrorHandlers,
} from "@/mocks/handlers";
import { server } from "@test/server";

import SmarterChat from "@/components/SmarterChat/Component";
import HeaderButton from "@/components/SmarterChat/HeaderButton";

vi.mock("mermaid", async () => ({ default: (await import("@/mocks/mermaid")).fakeMermaid }));

const WELCOME = "Welcome to Stackademy! How can I help you today?";

/** Types a message into the chat's input, and sends it with Enter. */
async function send(user: ReturnType<typeof userEvent.setup>, text: string) {
  await user.click(screen.getByRole("textbox", { name: "Message" }));
  await user.keyboard(`${text}{Enter}`);
}

/** The chat's root element, whose style has the LLMClient's styles' css variables. */
function chatRoot(): HTMLElement {
  return screen.getByRole("region", { name: "Chat" }).closest(".SmarterChat") as HTMLElement;
}

describe("SmarterChat", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    document.cookie = "csrftoken=the-csrf-token; path=/";
  });

  it("starts a new chat session with the LLMClient's welcome message and example prompts", async () => {
    server.use(...chatHandlers);
    render(<SmarterChat {...props} />);
    expect(screen.getByText("Configuring workbench...")).toBeInTheDocument();
    expect(await screen.findByText(WELCOME)).toBeInTheDocument();
    expect(screen.getByText("Some example prompts to get you started:")).toBeInTheDocument();
    expect(screen.getByText("Do you offer any courses on AI?", { selector: "li" })).toBeInTheDocument();
    expect(screen.getByText("Stackademy v1.0.0")).toBeInTheDocument();
    expect(screen.getByText("openai gpt-4o-mini with 2 additional tools")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "valid" })).toBeInTheDocument();
    expect(screen.getByText("(sandbox)")).toBeInTheDocument();
  });

  it("restores a chat session from its history, with its links", async () => {
    server.use(...historyHandlers);
    render(<SmarterChat {...props} />);
    const link = await screen.findByRole("link", { name: "the catalogue" });
    expect(link).toHaveAttribute("href", "https://stackademy.edu");
    expect(screen.getByText("Do you offer any courses on AI?")).toBeInTheDocument();
    expect(screen.getByText(/"course_code": "CS210"/)).toBeInTheDocument();
  });

  it("sends the thread with the user's message, and adds the response's messages", async () => {
    let body: { session_key: string; messages: { role: string; content: string }[] } | undefined;
    server.use(
      http.post(CONFIG_URL, () => HttpResponse.json({ data: config })),
      http.post(PROMPT_URL, async ({ request }) => {
        body = (await request.json()) as typeof body;
        return HttpResponse.json(promptResponse());
      }),
    );
    const user = userEvent.setup();
    render(<SmarterChat {...props} />);
    await screen.findByText(WELCOME);

    await send(user, "Any courses on AI?");

    expect(await screen.findByText("We offer CS210 Artificial Intelligence, for $700.00.")).toBeInTheDocument();
    expect(screen.getByText("Smarter selected the stackademy_sql plugin.")).toBeInTheDocument();
    expect(body?.session_key).toBe(SESSION_KEY);
    expect(body?.messages.map((message) => message.role)).toEqual(["system", "assistant", "assistant", "user"]);
    expect(body?.messages.at(-1)?.content).toBe("Any courses on AI?");
  });

  it("does not send an empty message", async () => {
    const prompt = vi.fn();
    server.use(
      http.post(CONFIG_URL, () => HttpResponse.json({ data: config })),
      http.post(PROMPT_URL, () => {
        prompt();
        return HttpResponse.json(promptResponse());
      }),
    );
    const user = userEvent.setup();
    render(<SmarterChat {...props} />);
    await screen.findByText(WELCOME);
    await send(user, "   ");
    expect(prompt).not.toHaveBeenCalled();
  });

  it("displays a failed prompt's error in the thread", async () => {
    server.use(...promptErrorHandlers);
    const user = userEvent.setup();
    render(<SmarterChat {...props} />);
    await screen.findByText(WELCOME);
    await send(user, "hello");
    expect(await screen.findByText("401 error: Incorrect API key provided.")).toBeInTheDocument();
  });

  it("explains an empty response that reached the max tokens, in sandbox mode", async () => {
    server.use(
      http.post(CONFIG_URL, () => HttpResponse.json({ data: config })),
      http.post(PROMPT_URL, () => HttpResponse.json(promptMaxTokensResponse())),
    );
    const user = userEvent.setup();
    render(<SmarterChat {...props} />);
    await screen.findByText(WELCOME);
    await send(user, "What is the weather in San Francisco?");

    const explanation = await screen.findByText(/The LLM reached this LLMClient's max tokens of 256/);
    expect(explanation).toHaveTextContent("so its response is empty. Raise defaultMaxTokens");

    await user.click(screen.getByRole("button", { name: "Production" }));
    expect(screen.queryByText(/The LLM reached this LLMClient's max tokens/)).not.toBeInTheDocument();
  });

  it("displays a network failure in the thread", async () => {
    server.use(
      http.post(CONFIG_URL, () => HttpResponse.json({ data: config })),
      http.post(PROMPT_URL, () => HttpResponse.error()),
    );
    const user = userEvent.setup();
    render(<SmarterChat {...props} />);
    await screen.findByText(WELCOME);
    await send(user, "hello");
    expect(await screen.findByText("Failed to fetch")).toBeInTheDocument();
  });

  it("hides and shows the backend's messages, in production and sandbox mode", async () => {
    server.use(...chatHandlers);
    const user = userEvent.setup();
    render(<SmarterChat {...props} />);
    await screen.findByText(WELCOME);
    expect(screen.getByText((config.llmclient.default_system_role ?? "").trim())).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Production" }));
    expect(screen.queryByText((config.llmclient.default_system_role ?? "").trim())).not.toBeInTheDocument();
    expect(screen.getByText(WELCOME)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Sandbox" }));
    expect(screen.getByText((config.llmclient.default_system_role ?? "").trim())).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sandbox" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Production" })).toHaveAttribute("aria-pressed", "false");
  });

  it("has no metadata toggle unless asked for one", async () => {
    server.use(...chatHandlers);
    render(<SmarterChat {...props} toggleMetadata={false} />);
    await screen.findByText(WELCOME);
    expect(screen.queryByRole("group", { name: "Chat mode" })).not.toBeInTheDocument();
  });

  it("displays only the conversation, as in production mode, without the metadata toggle", async () => {
    server.use(...chatHandlers);
    render(<SmarterChat {...props} toggleMetadata={false} />);
    await screen.findByText(WELCOME);
    expect(screen.queryByText((config.llmclient.default_system_role ?? "").trim())).not.toBeInTheDocument();
  });

  it("starts a new chat session without the old session's key", async () => {
    const sessionKeys: string[] = [];
    server.use(
      http.post(CONFIG_URL, async ({ request }) => {
        sessionKeys.push(((await request.json()) as { session_key: string }).session_key);
        return HttpResponse.json({ data: config });
      }),
    );
    const user = userEvent.setup();
    render(<SmarterChat {...props} />);
    await screen.findByText(WELCOME);
    await user.click(screen.getByRole("button", { name: "Start a new chat" }));
    await waitFor(() => expect(sessionKeys.length).toBeGreaterThanOrEqual(2));
    expect(sessionKeys.at(-1)).toBe("");
  });

  it("explains why the chat is unavailable when its configuration fails", async () => {
    server.use(...configErrorHandlers);
    render(<SmarterChat {...props} />);
    expect(await screen.findByText("LLMClient not found.")).toBeInTheDocument();
    expect(screen.getByText("Smarter Chat is not available")).toBeInTheDocument();
  });

  it("displays its own text in the language that it is asked for, but the LLMClient's as it is", async () => {
    server.use(...chatHandlers);
    render(<SmarterChat {...props} language="es-MX" />);
    expect(screen.getByText("Configurando el área de trabajo...")).toBeInTheDocument();
    expect(await screen.findByText(WELCOME)).toBeInTheDocument();
    expect(screen.getByText("Algunos prompts de ejemplo para empezar:")).toBeInTheDocument();
    expect(screen.getByText("openai gpt-4o-mini con 2 herramientas adicionales")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Iniciar un chat nuevo" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Modo del chat" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pruebas" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("textbox", { name: "Mensaje" })).toBeInTheDocument();
  });

  it("displays its own text in the page's language by default", async () => {
    server.use(...chatHandlers);
    document.documentElement.lang = "fr";
    render(<SmarterChat {...props} />);
    expect(await screen.findByText(WELCOME)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Démarrer un nouveau chat" })).toBeInTheDocument();
  });

  it("is still configuring while the configuration loads", () => {
    server.use(...loadingHandlers);
    render(<SmarterChat {...props} />);
    expect(screen.getByText("Configuring workbench...")).toBeInTheDocument();
  });

  it("sends an attached file's text", async () => {
    let lastMessage = "";
    server.use(
      http.post(CONFIG_URL, () =>
        HttpResponse.json({ data: { ...config, llmclient: { ...config.llmclient, app_file_attachment: true } } }),
      ),
      http.post(PROMPT_URL, async ({ request }) => {
        const body = (await request.json()) as { messages: { content: string }[] };
        lastMessage = body.messages.at(-1)!.content;
        return HttpResponse.json(promptResponse());
      }),
    );
    const user = userEvent.setup();
    render(<SmarterChat {...props} />);
    await screen.findByText(WELCOME);
    const file = new File(["print('hello')"], "hello.py", { type: "text/x-python" });
    await user.upload(screen.getByLabelText("Attach a file"), file);
    await waitFor(() => expect(lastMessage).toBe("print('hello')"));
    expect(screen.getByText("print('hello')")).toBeInTheDocument();
  });

  it("displays the prompt's progress while it runs, and replaces it with the response", async () => {
    let finish: () => void = () => {};
    server.use(
      http.post(CONFIG_URL, () => HttpResponse.json({ data: config })),
      http.post(PROMPT_URL, () => {
        const encoder = new TextEncoder();
        const [progress, result] = promptEventStream().split(": keepalive\n\n");
        const stream = new ReadableStream({
          start(controller) {
            controller.enqueue(encoder.encode(progress));
            finish = () => {
              controller.enqueue(encoder.encode(result));
              controller.close();
            };
          },
        });
        return new HttpResponse(stream, { headers: { "Content-Type": "text/event-stream" } });
      }),
    );
    const user = userEvent.setup();
    render(<SmarterChat {...props} />);
    await screen.findByText(WELCOME);
    await send(user, "Any courses on AI?");

    expect(await screen.findByText("Calling MCP server github: search_code")).toBeInTheDocument();
    expect(screen.getByText("Calling tool stackademy_sql")).toBeInTheDocument();
    const last = progressEvents.at(-1)!.message;
    expect(screen.getAllByText(last).length).toBeGreaterThan(0);
    expect(screen.getByText(`Stanley: ${last}`)).toBeInTheDocument();
    // the current step has a spinner, and the steps before it have a check mark. Both are css.
    // eslint-disable-next-line testing-library/no-node-access -- the steps are styled by their css class.
    const steps = Array.from(document.querySelectorAll("section.smarter-progress-message"));
    expect(steps.map((step) => step.classList.contains("smarter-progress-message-active"))).toEqual(
      progressEvents.map((_, index) => index === progressEvents.length - 1),
    );
    expect(steps.slice(0, -1).every((step) => step.classList.contains("smarter-progress-message-done"))).toBe(true);

    finish();
    expect(await screen.findByText("We offer CS210 Artificial Intelligence, for $700.00.")).toBeInTheDocument();
    expect(screen.queryByText("Calling tool stackademy_sql")).not.toBeInTheDocument();
  });

  it("does not ask for the prompt's progress unless asked to", async () => {
    let accept: string | null = null;
    server.use(
      http.post(CONFIG_URL, () => HttpResponse.json({ data: config })),
      http.post(PROMPT_URL, ({ request }) => {
        accept = request.headers.get("Accept");
        return HttpResponse.json(promptResponse());
      }),
    );
    const user = userEvent.setup();
    render(<SmarterChat {...props} streamProgress={false} />);
    await screen.findByText(WELCOME);
    await send(user, "hello");
    await screen.findByText("We offer CS210 Artificial Intelligence, for $700.00.");
    expect(accept).toBe("application/json");
  });

  it("hides the progress, but not the typing indicator's step, with the backend's messages", async () => {
    server.use(
      http.post(CONFIG_URL, () => HttpResponse.json({ data: config })),
      http.post(PROMPT_URL, () => {
        const stream = new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode(promptEventStream().split(": keepalive")[0]));
          },
        });
        return new HttpResponse(stream, { headers: { "Content-Type": "text/event-stream" } });
      }),
    );
    const user = userEvent.setup();
    render(<SmarterChat {...props} />);
    await screen.findByText(WELCOME);
    await user.click(screen.getByRole("button", { name: "Production" }));
    await send(user, "hello");
    expect(await screen.findByText(`Stanley: ${progressEvents.at(-1)!.message}`)).toBeInTheDocument();
    expect(screen.queryByText("Calling tool stackademy_sql")).not.toBeInTheDocument();
  });

  it("displays markdown images, sized for their chat bubble", async () => {
    server.use(http.post(CONFIG_URL, () => HttpResponse.json({ data: configWithImages })));
    render(<SmarterChat {...props} />);
    const banner = await screen.findByRole("img", { name: "CS210 course banner" });
    expect(banner).toHaveClass("smarter-chat-image");
    // a data url, which browsers don't open, so it isn't a link.
    expect(screen.queryByRole("link", { name: "CS210 course banner" })).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: "the catalogue" })).toHaveClass("smarter-chat-image");
    expect(screen.getByRole("link", { name: "the catalogue" })).toHaveAttribute("href", "https://stackademy.edu");
  });

  it("replaces a markdown image that fails to load with its description", async () => {
    server.use(http.post(CONFIG_URL, () => HttpResponse.json({ data: configWithImages })));
    render(<SmarterChat {...props} />);
    const catalogue = await screen.findByRole("img", { name: "the catalogue" });
    fireEvent.error(catalogue);
    expect(screen.queryByRole("img", { name: "the catalogue" })).not.toBeInTheDocument();
    // the link to the image's page stays, with the image's description.
    expect(screen.getByRole("link", { name: "the catalogue" })).toHaveAttribute("href", "https://stackademy.edu");
  });

  it("applies the LLMClient's styles: its colors, font, logo and avatars", async () => {
    server.use(http.post(CONFIG_URL, () => HttpResponse.json({ data: configWithStyles })));
    render(<SmarterChat {...props} />);
    await screen.findByText("CS301 Applied AI");
    const root = chatRoot();
    expect(root.style.getPropertyValue("--smarter-chat-header-bg")).toBe("#14213d");
    expect(root.style.getPropertyValue("--smarter-chat-outgoing-bg")).toBe("#fca311");
    expect(root.style.getPropertyValue("--smarter-chat-font-family")).toBe('"Nunito", system-ui, sans-serif');
    // the font's stylesheet link is added by an effect, which can run after the text is displayed.
    await waitFor(() =>
      // eslint-disable-next-line testing-library/no-node-access -- the font's stylesheet is a link in the page's head.
      expect(document.getElementById("smarter-chat-google-font")).toHaveAttribute(
        "href",
        expect.stringContaining("family=Nunito"),
      ),
    );
    expect(screen.getByRole("img", { name: "Stackademy" })).toHaveAttribute("src", chatStyles.app_logo_url);
    expect(screen.getAllByRole("img", { name: "Stanley" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("img", { name: "You" })).toHaveAttribute("src", chatStyles.user_avatar_url);
  });

  it("hides a logo or avatar whose image fails to load", async () => {
    server.use(http.post(CONFIG_URL, () => HttpResponse.json({ data: configWithStyles })));
    render(<SmarterChat {...props} />);
    await screen.findByText("CS301 Applied AI");
    fireEvent.error(screen.getByRole("img", { name: "You" }));
    await waitFor(() => expect(screen.queryByRole("img", { name: "You" })).not.toBeInTheDocument());
    expect(screen.getByRole("img", { name: "Stackademy" })).toBeInTheDocument();
  });

  it("has no logo, avatars or style variables without styles", async () => {
    server.use(...chatHandlers);
    render(<SmarterChat {...props} />);
    await screen.findByText(WELCOME);
    expect(chatRoot().getAttribute("style")).toBeFalsy();
    expect(screen.queryByRole("img", { name: "Stackademy" })).not.toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "Stanley" })).not.toBeInTheDocument();
  });

  it("highlights code blocks, and copies their code", async () => {
    server.use(http.post(CONFIG_URL, () => HttpResponse.json({ data: configWithCode })));
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    render(<SmarterChat {...props} />);
    const copy = await screen.findByRole("button", { name: "Copy code" });
    expect(screen.getByText("python")).toHaveClass("smarter-chat-code-language");
    expect(screen.getByText('"CS210"')).toHaveClass("hljs-string");

    fireEvent.click(copy);
    expect(writeText).toHaveBeenCalledWith('import stackademy\n\nstackademy.enroll("CS210")');
    await waitFor(() => expect(copy).toHaveTextContent("Copied!"));
  });

  it("displays mermaid code blocks as diagrams, and shows their code", async () => {
    server.use(http.post(CONFIG_URL, () => HttpResponse.json({ data: configWithDiagram })));
    const user = userEvent.setup();
    render(<SmarterChat {...props} />);
    const diagram = await screen.findByRole("figure", { name: "Diagram" });
    expect(screen.getByText("mermaid")).toHaveClass("smarter-chat-code-language");
    expect(screen.getByText(/Browse the catalogue/, { selector: "pre code" })).not.toBeVisible();

    await user.click(screen.getByRole("button", { name: "Show the diagram's code" }));
    expect(diagram).not.toBeVisible();
    expect(screen.getByText(/Browse the catalogue/, { selector: "pre code" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Show the diagram" })).toHaveTextContent("Diagram");
  });

  it("adds the page's buttons to its header, after its own", async () => {
    server.use(...chatHandlers);
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <SmarterChat
        {...props}
        headerActions={
          <HeaderButton className="extra" onClick={onClick}>
            Docs
          </HeaderButton>
        }
      />,
    );
    await screen.findByText(WELCOME);
    const docs = screen.getByRole("button", { name: "Docs" });
    expect(docs).toHaveClass("smarter-chat-toolbar-button", "extra");
    await user.click(docs);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("puts a header button's label in its own element, and passes its ref to the button", async () => {
    server.use(...chatHandlers);
    const ref = createRef<HTMLButtonElement>();
    render(
      <SmarterChat
        {...props}
        headerActions={
          <>
            <HeaderButton ref={ref}>Help</HeaderButton>
            <HeaderButton aria-label="Icon only" />
          </>
        }
      />,
    );
    await screen.findByText(WELCOME);
    const help = screen.getByRole("button", { name: "Help" });
    expect(ref.current).toBe(help);
    expect(screen.getByText("Help")).toHaveClass("smarter-chat-toolbar-label");
    expect(screen.getByRole("button", { name: "Icon only" })).not.toHaveClass("smarter-chat-toolbar-button-labeled");
  });

  it("passes the configuration, the mode and new chats to the page", async () => {
    server.use(...chatHandlers);
    const user = userEvent.setup();
    const onConfig = vi.fn();
    const onModeChange = vi.fn();
    const onNewChat = vi.fn();
    render(<SmarterChat {...props} onConfig={onConfig} onModeChange={onModeChange} onNewChat={onNewChat} />);
    await screen.findByText(WELCOME);
    await waitFor(() => expect(onConfig).toHaveBeenCalledWith(expect.objectContaining({ session_key: SESSION_KEY })));
    expect(onModeChange).toHaveBeenLastCalledWith(true);

    await user.click(screen.getByRole("button", { name: "Production" }));
    expect(onModeChange).toHaveBeenLastCalledWith(false);
    // the current mode's option changes nothing.
    const calls = onModeChange.mock.calls.length;
    await user.click(screen.getByRole("button", { name: "Production" }));
    expect(onModeChange).toHaveBeenCalledTimes(calls);

    await user.click(screen.getByRole("button", { name: "Start a new chat" }));
    expect(onNewChat).toHaveBeenCalledOnce();
    await waitFor(() => expect(onConfig).toHaveBeenCalledTimes(2));
  });

  it("reloads the configuration when the page asks it to, and the chat session continues", async () => {
    server.use(...chatHandlers);
    const { rerender } = render(<SmarterChat {...props} reloadKey={0} />);
    await screen.findByText("Stackademy v1.0.0");

    const renamed = { ...config, llmclient: { ...config.llmclient, app_name: "Stackademy Renamed" } };
    server.use(http.post(CONFIG_URL, () => HttpResponse.json({ data: renamed, api: "smarter.sh/v1" })));
    rerender(<SmarterChat {...props} reloadKey={0} />);
    expect(screen.getByText("Stackademy v1.0.0")).toBeInTheDocument();
    rerender(<SmarterChat {...props} reloadKey={1} />);
    expect(await screen.findByText("Stackademy Renamed v1.0.0")).toBeInTheDocument();
    expect(screen.getByText(WELCOME)).toBeInTheDocument();
  });

  it("logs a failed reload, and keeps the chat", async () => {
    server.use(...chatHandlers);
    const { rerender } = render(<SmarterChat {...props} reloadKey={0} />);
    await screen.findByText(WELCOME);
    server.use(...configErrorHandlers);
    rerender(<SmarterChat {...props} reloadKey={1} />);
    await waitFor(() =>
      expect(console.error).toHaveBeenCalledWith(expect.stringContaining("Failed to refresh"), expect.anything()),
    );
    expect(screen.getByText(WELCOME)).toBeInTheDocument();
  });
});

describe("SmarterChat's verbose configuration", () => {
  /** The config api's requests, as whether each asked for the diagnostic parts, with ?verbose=true. */
  function recordConfigRequests(): boolean[] {
    const requests: boolean[] = [];
    server.use(
      http.post(CONFIG_URL, ({ request }) => {
        const verbose = new URL(request.url).searchParams.get("verbose") === "true";
        requests.push(verbose);
        return HttpResponse.json({ data: verbose ? configWithHistory : leanConfig(configWithHistory) });
      }),
      http.post(PROMPT_URL, () => HttpResponse.json(promptResponse())),
    );
    return requests;
  }

  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    document.cookie = "csrftoken=the-csrf-token; path=/";
  });

  it("asks for the diagnostic parts with verbose", async () => {
    const requests = recordConfigRequests();
    render(<SmarterChat {...props} verbose />);
    await screen.findByRole("link", { name: "the catalogue" });
    await waitFor(() => expect(requests).toEqual([true]));
  });

  it("never asks for the diagnostic parts without verbose, nor refreshes after a prompt", async () => {
    const requests = recordConfigRequests();
    const user = userEvent.setup();
    render(<SmarterChat {...props} />);
    await screen.findByRole("link", { name: "the catalogue" });
    await send(user, "Any courses on AI?");
    expect(await screen.findByText("We offer CS210 Artificial Intelligence, for $700.00.")).toBeInTheDocument();
    expect(requests).toEqual([false]);
  });

  it("fetches the diagnostic parts when verbose is turned on, and again after a prompt changed them", async () => {
    const requests = recordConfigRequests();
    const user = userEvent.setup();
    const onConfig = vi.fn();
    const { rerender } = render(<SmarterChat {...props} onConfig={onConfig} />);
    await screen.findByRole("link", { name: "the catalogue" });
    expect(requests).toEqual([false]);

    // a prompt without verbose doesn't refresh the configuration.
    await send(user, "Any courses on AI?");
    expect(await screen.findByText("We offer CS210 Artificial Intelligence, for $700.00.")).toBeInTheDocument();
    expect(requests).toEqual([false]);

    rerender(<SmarterChat {...props} onConfig={onConfig} verbose />);
    await waitFor(() => expect(requests).toEqual([false, true]));
    await waitFor(() =>
      expect(onConfig).toHaveBeenLastCalledWith(
        expect.objectContaining({ history: expect.objectContaining({ prompt_tool_call_history: expect.any(Array) }) }),
      ),
    );

    // off, and on again: the diagnostic parts are current.
    rerender(<SmarterChat {...props} onConfig={onConfig} />);
    rerender(<SmarterChat {...props} onConfig={onConfig} verbose />);
    expect(requests).toEqual([false, true]);

    // a prompt with verbose refreshes them.
    await send(user, "And on databases?");
    await waitFor(() => expect(requests).toEqual([false, true, true]));
  });

  it("refetches the diagnostic parts that a prompt changed while verbose was off", async () => {
    const requests = recordConfigRequests();
    const user = userEvent.setup();
    const { rerender } = render(<SmarterChat {...props} verbose />);
    await screen.findByRole("link", { name: "the catalogue" });
    await waitFor(() => expect(requests).toEqual([true]));

    rerender(<SmarterChat {...props} />);
    await send(user, "Any courses on AI?");
    expect(await screen.findByText("We offer CS210 Artificial Intelligence, for $700.00.")).toBeInTheDocument();
    expect(requests).toEqual([true]);
    rerender(<SmarterChat {...props} verbose />);
    await waitFor(() => expect(requests).toEqual([true, true]));
  });
});
