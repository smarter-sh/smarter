/**
 * The technical references that the Docs dialog links to, grouped by audience. They are functions, rather than
 * constants, so that their text is translated into the language that is active when the dialog opens. The links'
 * titles are the titles of the documentation's pages, which are in English, and aren't translated.
 */
import { gettext } from "@smarter/common";

/** A technical reference that the Docs dialog links to. */
export interface DocLink {
  title: string;
  url: string;
  description: string;
}

/** A tab of the Docs dialog: the technical references for one audience. */
export interface DocSection {
  title: string;
  description: string;
  links: DocLink[];
}

/** The technical references for prompt engineers, who build LLMClients in the sandbox. */
export function promptEngineerLinks(): DocLink[] {
  return [
    {
      title: "Smarter Chat",
      url: "https://docs.smarter.sh/smarter-framework/smarter-chat.html",
      description: gettext("The chat workbench: sandbox and production modes, the Console, and the server logs."),
    },
    {
      title: "LLMClient",
      url: "https://docs.smarter.sh/smarter-resources/smarter-llmclient.html",
      description: gettext("The LLMClient class, which is the main interface to the Smarter API."),
    },
    {
      title: "LLM Tools",
      url: "https://docs.smarter.sh/smarter-framework/extensibility.html",
      description: gettext("How to leverage LLM tool calling with Smarter."),
    },
    {
      title: "Guardrail",
      url: "https://docs.smarter.sh/smarter-resources/smarter-guardrail.html",
      description: gettext("How to create and use guardrails with the Smarter API."),
    },
    {
      title: "Budget",
      url: "https://docs.smarter.sh/smarter-resources/smarter-budget.html",
      description: gettext("How to create and use budgets with the Smarter API."),
    },
  ];
}

/** The technical references for software engineers, who build the applications that host them. */
export function softwareEngineerLinks(): DocLink[] {
  return [
    {
      title: "@smarter.sh/ui-chat",
      url: "https://www.npmjs.com/package/@smarter.sh/ui-chat",
      description: gettext("The npm package of this chat component, its props, and how to install it."),
    },
    {
      title: "Smarter Chat API",
      url: "https://docs.smarter.sh/smarter-framework/smarter-api/chat.html",
      description: gettext("The REST api behind the chat: its configuration and prompt endpoints."),
    },
    {
      title: "React integration",
      url: "https://docs.smarter.sh/smarter-framework/developer-reference/react-integration.html",
      description: gettext("How to host a Smarter chatbot in your own React application."),
    },
    {
      title: "Smarter on Kubernetes",
      url: "https://docs.smarter.sh/smarter-framework/smarter-on-kubernetes.html",
      description: gettext("What deploying an LLMClient creates in Kubernetes, and how to operate it in production."),
    },
  ];
}

/** The tabs of the Docs dialog, from left to right. The first one is selected when it opens. */
export function docSections(): DocSection[] {
  return [
    {
      title: gettext("Prompt Engineer"),
      description: gettext("Building and testing LLMClients in the sandbox."),
      links: promptEngineerLinks(),
    },
    {
      title: gettext("Software Engineer"),
      description: gettext("Hosting an LLMClient in your own application."),
      links: softwareEngineerLinks(),
    },
  ];
}
