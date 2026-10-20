/**
 * The steps of the workbench's guided tour, for a new user who has never written code and knows little about
 * generative AI yet: what each part of the workbench is, and what it is for, in plain words.
 *
 * A step about a part that this page doesn't have, e.g. the Server Logs tab when the server logs are off, or
 * the Console in production mode, is left out. The chat's parts are found by Smarter Chat's own class names
 * (@smarter.sh/ui-chat, and the chatscope components that it is built with), and the Console's tabs by their
 * ids, see Console/enums.ts. A step about a tab selects it, so that the Console shows what the step is about.
 */
import { gettext } from "@smarter/common";
import type { TourStep } from "@smarter/onboarding";

import { MenuItems } from "@/components/Console/enums";

/** The Console's tab for the menu item, scoped to the Console, whose tabs' ids are its menu items. */
const consoleTab = (item: string) => `#chatapp_console [id="${item}"]`;

export function workbenchTourSteps(): TourStep[] {
  return [
    {
      icon: "ki-rocket",
      title: gettext("Welcome to the Prompt Engineer's Workbench"),
      text: gettext(
        "This is where you talk to an LLMClient, and see how it works behind the scenes. An LLMClient is an AI application, such as a chatbot, built on a large language model, an LLM. This short tour shows you around.",
      ),
    },
    {
      target: ".smarter-chat-message-list",
      icon: "ki-message-text-2",
      title: gettext("The chat"),
      text: gettext(
        "On the left is the conversation. It works like the AI chat apps that you may know: you write a message, and the LLMClient answers. Smarter sends your message to the LLM, together with the LLMClient's instructions.",
      ),
    },
    {
      target: ".cs-message-input",
      icon: "ki-message-edit",
      title: gettext("Ask a question"),
      text: gettext(
        "Type your message here, and press Enter to send it. With the weather LLMClient, try: What's the weather in Vancouver today?",
      ),
    },
    {
      target: ".smarter-chat-mode-toggle",
      icon: "ki-switch",
      title: gettext("Sandbox and production modes"),
      text: gettext(
        "In sandbox mode, the chat also shows what Smarter does behind the scenes, step by step. Production mode shows only the conversation, as the LLMClient's users would see it. The button beside it starts a new chat.",
      ),
    },
    {
      target: ".smarter-workbench-console-toggle",
      icon: "ki-code",
      title: gettext("The Console"),
      text: gettext(
        "This button shows and hides the Console, on the right: your window into how the LLMClient works. Drag the bar between the chat and the Console to make either one wider.",
      ),
    },
    {
      activate: true,
      target: consoleTab(MenuItems.MANIFEST),
      icon: "ki-document",
      title: gettext("The manifest"),
      text: gettext(
        "Every LLMClient is described by a short text file, its manifest: which LLM it uses, its instructions, which are called its system prompt, and its tools. Change it here and save, and the chat uses your changes right away. No programming needed.",
      ),
    },
    {
      activate: true,
      target: consoleTab(MenuItems.ARCHITECTURE),
      icon: "ki-abstract-26",
      title: gettext("The architecture"),
      text: gettext(
        "A diagram of everything that this LLMClient is built from, such as its tools, its secrets and its api key, with suggestions for what to add next.",
      ),
    },
    {
      activate: true,
      target: consoleTab(MenuItems.SERVER_LOGS),
      icon: "ki-notepad",
      title: gettext("Server logs"),
      text: gettext(
        "The messages that the Smarter server writes while it answers your prompts, as they happen. They help when something doesn't work as you expect.",
      ),
    },
    {
      activate: true,
      target: consoleTab(MenuItems.CHAT_TOOL_CALL_HISTORY),
      icon: "ki-wrench",
      title: gettext("Tool calls"),
      text: gettext(
        "An LLM can't look up today's weather by itself. Instead, it asks Smarter to run a tool, such as get_weather, and answers from the result. Each tool call of this chat shows up here.",
      ),
    },
    {
      activate: true,
      target: consoleTab(MenuItems.CHAT_CONFIG),
      icon: "ki-setting-3",
      title: gettext("Config"),
      text: gettext(
        "The complete configuration that the chat received from Smarter: everything that the LLMClient is set up with, for reference.",
      ),
    },
    {
      activate: true,
      target: consoleTab(MenuItems.DEPLOYMENT),
      icon: "ki-send",
      title: gettext("Deployment"),
      text: gettext(
        "When your LLMClient is ready, deploy it, to give it its own web address that people and other programs can use. This tab shows how.",
      ),
    },
    {
      target: ".smarter-workbench-help-button",
      icon: "ki-medal-star",
      title: gettext("Now try it yourself"),
      text: gettext(
        "Ask the LLMClient a question, then look at the Console's Tool Calls and Server Logs tabs to see what happened. The Help menu has links to the documentation, and takes you on this tour again at any time.",
      ),
    },
  ];
}
