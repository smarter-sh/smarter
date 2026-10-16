/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import { gettext, TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";
import type { LLMClient, LLMClientListViewProps, LLMClientCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: gettext("Your LLM Clients") },
  { key: "shared" as TabKey, label: gettext("Shared LLM Clients") },
];

// Set the TabbedViewContext generic object type to LLMClient,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type ProviderTabbedViewContext = Omit<TabbedViewContext<LLMClient>, "ListView" | "CardView"> & {
  ListView: React.ComponentType<LLMClientListViewProps>;
  CardView: React.ComponentType<LLMClientCardViewProps>;
};

const providerTabbedListViewContext: ProviderTabbedViewContext = {
  objectType: {} as LLMClient,
  objectTypeName: "llmclient",
  tabs: tabs,
  ListView: ListView,
  CardView: CardView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = gettext("LLM Clients (aka 'Harnesses')");
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-llmclient.html";
  const helpText = gettext(
    "LLMClients implement what is commonly known as an LLM 'harness': the execution environment around a large language model. An LLMClient manages the prompts, conversation state, tool calls, configuration, security and runtime behavior that turn a foundation model into a reliable, production-ready application. LLMClients serve interactive conversations with people and fully automated workflows, whether called directly through the API or attached to an Orchestrator. Beyond sending requests to the model, an LLMClient can call Smarter Plugins to fetch data from private systems and external APIs, use the tools of remote MCP servers through MCPClients (experimental), and apply Guardrails that moderate both the user's input and the model's output. ",
  );
  return (
    <>
      <section className="mt-5 mb-5 container" id="llmclient-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={providerTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
