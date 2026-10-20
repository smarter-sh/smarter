/**
 * The welcome dialog's steps: a short tour of what Smarter is, what the new account holds, what
 * it teaches, MCP servers, RAG with Vectorstores, how it hosts open models, how it runs in production on
 * Kubernetes, and where to start. The text follows the
 * welcome email that the new user received, templates/account/email/welcome.html, so that the
 * two read as one message.
 *
 * Each step's illustration is from the Keen theme's dozzy-1 set, in the console's static files,
 * which has a version for the light theme (<n>.png) and one for the dark theme (<n>-dark.png).
 */
import { gettext, interpolate } from "@smarter/common";

/** One of a step's highlights: a Keen icon, a title, and a sentence. */
export interface WelcomeHighlight {
  icon: string;
  title: string;
  description: string;
}

export interface WelcomeStep {
  /** The illustration's number in the dozzy-1 set. */
  illustration: number;
  title: string;
  lead: string;
  highlights: WelcomeHighlight[];
}

/** The dialog's steps, in order. The last one also shows the links. */
export function welcomeSteps(firstName: string): WelcomeStep[] {
  return [
    {
      illustration: 1,
      title: firstName
        ? interpolate(gettext("Welcome to Smarter, %(firstName)s!"), { firstName })
        : gettext("Welcome to Smarter!"),
      lead: gettext(
        "Smarter is a platform for designing and running the kinds of sophisticated AI solutions that large organizations require. It is made for non-programmers.",
      ),
      highlights: [
        {
          icon: "ki-code",
          title: gettext("Free and open source"),
          description: gettext(
            "Licensed under the GNU AGPL v3. Download it, read its source code, and run it on your laptop.",
          ),
        },
        {
          icon: "ki-teacher",
          title: gettext("Made for learning"),
          description: gettext("A hands-on place to learn how real AI solutions are designed and built."),
        },
        {
          icon: "ki-note-2",
          title: gettext("No code required"),
          description: gettext("Every resource is a short YAML manifest that you can read, copy and change."),
        },
      ],
    },
    {
      illustration: 2,
      title: gettext("Your account is ready to explore"),
      lead: gettext(
        "Your new account is preloaded with dozens of AI resources and solutions. Open any of them to see how it works, then customize it and make it your own.",
      ),
      highlights: [
        {
          icon: "ki-message-programming",
          title: gettext("LLMClients"),
          description: gettext("Chatbots, agents and harnesses, each with its own LLM, system prompt and tools."),
        },
        {
          icon: "ki-cube-2",
          title: gettext("LLM Tools"),
          description: gettext("Tool calling that connects an LLM to SQL databases, REST APIs, web search and more."),
        },
        {
          icon: "ki-shield-tick",
          title: gettext("Guardrails, secrets, API keys and budgets"),
          description: gettext(
            "The controls that organizations need to run AI safely and affordably, such as API keys that secure your LLMClients.",
          ),
        },
      ],
    },
    {
      illustration: 13,
      title: gettext("Get hands-on with the real thing"),
      lead: gettext(
        "Smarter supports popular generative AI technologies, vendors, protocols and best practices. It's a good place to try them out and learn how they work.",
      ),
      highlights: [
        {
          icon: "ki-technology-2",
          title: gettext("Thousands of LLMs from nine providers"),
          description: gettext(
            "Anthropic, Cohere, Fireworks AI, Google AI, Hugging Face, Meta AI, Mistral, OpenAI and Together AI, side by side.",
          ),
        },
        {
          icon: "ki-electricity",
          title: gettext("MCP, Agent Skills and tool calling"),
          description: gettext("Connect LLMs to tools and data with the protocols that the industry uses."),
        },
        {
          icon: "ki-dollar",
          title: gettext("Real prompts, real costs"),
          description: gettext(
            "Every prompt is a real, billable request to an LLM provider. Experiment freely, but please don't run automated loads.",
          ),
        },
      ],
    },
    {
      // Smarter's resource kind is MCPClient: Smarter is the client of a remote MCP server. The
      // welcome dialog says "MCP Servers", which is what a new user knows them as.
      illustration: 5,
      title: gettext("Connect MCP Servers"),
      lead: gettext(
        "MCP Servers give your LLMClients the tools of other services, through the Model Context Protocol. Connect one, and its tools are ready for your LLMClients to use, with no code to write.",
      ),
      highlights: [
        {
          icon: "ki-element-11",
          title: gettext("Dozens ready to connect"),
          description: gettext("GitHub, Hugging Face, Notion, Linear, Sentry, Stripe and many more."),
        },
        {
          icon: "ki-lock",
          title: gettext("Your credentials stay secret"),
          description: gettext(
            "A server's access token is kept in an encrypted Smarter Secret, and you choose which of its tools the LLM may call.",
          ),
        },
        {
          icon: "ki-shield-tick",
          title: gettext("Governed like everything else"),
          description: gettext(
            "Every tool call is logged and charged, and is subject to the same access controls as your other resources.",
          ),
        },
      ],
    },
    {
      illustration: 19,
      title: gettext("Answer from your own documents"),
      lead: gettext(
        "Retrieval-augmented generation (RAG) lets an LLM answer from your own material, such as manuals, policies and support articles, rather than from its training data alone.",
      ),
      highlights: [
        {
          icon: "ki-data",
          title: gettext("Vectorstores"),
          description: gettext(
            "Vector databases, Qdrant or Pinecone, that Smarter creates and manages for you. Add PDFs, text, web pages and more, and Smarter splits, embeds and loads them.",
          ),
        },
        {
          icon: "ki-magnifier",
          title: gettext("Search by meaning"),
          description: gettext(
            "A question finds the passages that are closest to it in meaning, not just those that share its words, and the LLM answers from them.",
          ),
        },
        {
          icon: "ki-dollar",
          title: gettext("Real databases, real costs"),
          description: gettext(
            "A Vectorstore runs on real cloud infrastructure, which costs real money for as long as it exists, whether or not anyone searches it.",
          ),
        },
      ],
    },
    {
      illustration: 9,
      title: gettext("Host open models yourself"),
      lead: gettext(
        "LLMHosts run open-weight models on your own GPU servers, rather than calling a provider's API. Your LLMClients use them just as they use a commercial model.",
      ),
      highlights: [
        {
          icon: "ki-cloud-download",
          title: gettext("Models from Hugging Face"),
          description: gettext(
            "Choose a model and a revision, and Smarter deploys it on Kubernetes with an inference engine such as vLLM.",
          ),
        },
        {
          icon: "ki-setting-2",
          title: gettext("You choose the hardware"),
          description: gettext(
            "Pick the kind of GPU node that the model runs on, and how much of it each replica gets.",
          ),
        },
        {
          icon: "ki-dollar",
          title: gettext("Real servers, real costs"),
          description: gettext(
            "An LLMHost runs on real cloud infrastructure, which costs real money for as long as it runs, whether or not anyone sends it a prompt.",
          ),
        },
      ],
    },
    {
      illustration: 6,
      title: gettext("Built for production, at scale"),
      lead: gettext(
        "Smarter runs AI solutions in production on Kubernetes, the same cloud orchestration technology behind global platforms such as Netflix, YouTube and TikTok.",
      ),
      highlights: [
        {
          icon: "ki-cloud",
          title: gettext("State-of-the-art orchestration"),
          description: gettext(
            "Kubernetes grew out of Borg, the system that runs Google's services, YouTube among them. Netflix and ByteDance, TikTok's parent, run their platforms on it too.",
          ),
        },
        {
          icon: "ki-graph-up",
          title: gettext("Grows with demand"),
          description: gettext(
            "Smarter's web servers and workers run as several copies, Kubernetes replaces any that fail, and the cluster adds servers when they need more room.",
          ),
        },
        {
          icon: "ki-shield-tick",
          title: gettext("Every LLMClient at its own url"),
          description: gettext(
            "Deploying an LLMClient gives it its own host name, with a TLS certificate that the cluster issues and renews by itself.",
          ),
        },
      ],
    },
    {
      illustration: 4,
      title: gettext("Where to start"),
      lead: gettext("A few good first stops on your journey:"),
      highlights: [],
    },
  ];
}
