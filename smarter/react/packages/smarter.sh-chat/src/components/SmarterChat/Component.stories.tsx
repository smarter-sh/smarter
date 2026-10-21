import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";

import { props } from "@/mocks/fixtures";
import {
  chatHandlers,
  configErrorHandlers,
  diagramHandlers,
  historyHandlers,
  imageHandlers,
  loadingHandlers,
  mathHandlers,
  promptErrorHandlers,
  streamingHandlers,
  stylesHandlers,
} from "@/mocks/handlers";

import SmarterChat from "@/components/SmarterChat/Component";

/** A chat with a Smarter LLMClient, in sandbox mode, as the web console's workbench renders it. */
const meta = {
  title: "Smarter Chat/SmarterChat",
  component: SmarterChat,
  args: props,
  decorators: [
    (Story) => (
      <div style={{ height: "88vh" }}>
        <Story />
      </div>
    ),
  ],
  parameters: { layout: "fullscreen", msw: { handlers: chatHandlers } },
} satisfies Meta<typeof SmarterChat>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A new chat session: the welcome message and example prompts. */
export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Welcome to Stackademy! How can I help you today?")).toBeInTheDocument();
  },
};

/** A chat session in progress, restored from its history. */
export const WithHistory: Story = {
  parameters: { msw: { handlers: historyHandlers } },
};

/** The user sends a prompt, and the response's messages are added to the thread. */
export const SendPrompt: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await canvas.findByText("Welcome to Stackademy! How can I help you today?");
    await userEvent.click(canvas.getByRole("textbox", { name: "Message" }));
    await userEvent.keyboard("Do you offer any courses on AI?{Enter}");
    await expect(await canvas.findByText("We offer CS210 Artificial Intelligence, for $700.00.")).toBeInTheDocument();
  },
};

/** The chat's own text in Spanish, as the language prop asks. The LLMClient's own text is displayed as it is. */
export const Spanish: Story = {
  args: { language: "es" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await canvas.findByText("Welcome to Stackademy! How can I help you today?");
    await expect(canvas.getByRole("button", { name: "Iniciar un chat nuevo" })).toBeInTheDocument();
  },
};

/** The chat's own text in French. */
export const French: Story = {
  args: { language: "fr" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await canvas.findByText("Welcome to Stackademy! How can I help you today?");
    await expect(canvas.getByRole("button", { name: "Démarrer un nouveau chat" })).toBeInTheDocument();
  },
};

/** The LLM provider rejects the prompt, and its error is displayed in the thread. */

export const PromptError: Story = {
  parameters: { msw: { handlers: promptErrorHandlers } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await canvas.findByText("Welcome to Stackademy! How can I help you today?");
    await userEvent.click(canvas.getByRole("textbox", { name: "Message" }));
    await userEvent.keyboard("hello{Enter}");
    await expect(await canvas.findByText("401 error: Incorrect API key provided.")).toBeInTheDocument();
  },
};

/** The configuration has not arrived yet. */
export const Loading: Story = {
  parameters: { msw: { handlers: loadingHandlers } },
};

/** The configuration api failed. */
export const ConfigError: Story = {
  parameters: { msw: { handlers: configErrorHandlers } },
};

/**
 * A narrow chat, as beside the workbench's Console: the header's buttons show only their icons. Their labels
 * still name them for screen readers.
 */
export const Narrow: Story = {
  decorators: [
    (Story) => (
      <div style={{ width: 420, height: "100%" }}>
        <Story />
      </div>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await canvas.findByText("Welcome to Stackademy! How can I help you today?");
    await expect(canvas.getByRole("button", { name: "Production" })).toHaveAttribute("aria-pressed", "false");
  },
};

/** The conversation only, as a bespoke web page renders it, without the mode toggle. */
export const Conversation: Story = {
  args: { toggleMetadata: false },
};

/**
 * The prompt api streams the prompt's progress: its LLM requests, tool calls and MCP server
 * requests are displayed while it runs, and are replaced by the response.
 */
export const StreamingProgress: Story = {
  parameters: { msw: { handlers: streamingHandlers } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await canvas.findByText("Welcome to Stackademy! How can I help you today?");
    await userEvent.click(canvas.getByRole("textbox", { name: "Message" }));
    await userEvent.keyboard("Do you offer any courses on AI?{Enter}");
    await expect(await canvas.findByText("Sending the prompt to the LLM")).toBeInTheDocument();
  },
};

/** The assistant replied with markdown images, which are sized to fit their chat bubble. */
export const WithImages: Story = {
  parameters: { msw: { handlers: imageHandlers } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("img", { name: "CS210 course banner" })).toBeInTheDocument();
  },
};

/**
 * An LLMClient with styles (its manifest's spec.config.styles): a logo in the header, avatars beside
 * the messages, a background image, a Google font, and its own colors.
 */
export const WithStyles: Story = {
  parameters: { msw: { handlers: stylesHandlers } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("CS301 Applied AI")).toBeInTheDocument();
  },
};

/** The assistant replied with a mermaid code block, which is displayed as its diagram. */
export const WithDiagram: Story = {
  parameters: { msw: { handlers: diagramHandlers } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const diagram = await canvas.findByRole("figure", { name: "Diagram" }, { timeout: 10000 });
    await expect(diagram.querySelector("svg")).toBeInTheDocument();
    await userEvent.click(canvas.getByRole("button", { name: "Show the diagram's code" }));
    await expect(diagram).not.toBeVisible();
    await userEvent.click(canvas.getByRole("button", { name: "Show the diagram" }));
    await expect(diagram).toBeVisible();
  },
};

/** The assistant replied with math, in LaTeX, which is typeset: inline, and displayed. */
export const WithMath: Story = {
  parameters: { msw: { handlers: mathHandlers } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const paragraph = await canvas.findByText(/Each term is the sum of the two before it/, { selector: "p" });
    await expect(paragraph.querySelectorAll(".katex")).toHaveLength(3);
    await expect(canvasElement.querySelector(".katex-display")).toBeInTheDocument();
  },
};
