/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import { TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";
import type { LLMClient, LLMClientListViewProps, LLMClientCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your LLM Clients" },
  { key: "shared" as TabKey, label: "Shared LLM Clients" },
];

// Set the TabbedViewContext generic object type to LLMClient,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type ProviderTabbedViewContext = Omit<
  TabbedViewContext<LLMClient>,
  "ListView" | "CardView"
> & {
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
  const title = "LLM Clients (aka 'Harnesses')";
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-llmclient.html";
  const helpText = "LLMClients implement of what is commonly known as an LLM 'Harness'. It provides the execution environment surrounding a large language model, managing the prompts, conversation state, tool execution, configuration, security, and runtime behavior required to transform a foundation model into a reliable, production-ready application. LLMClients support both interactive conversations with human users and fully automated workflows. In addition to orchestrating requests to a language model, they leverage the Smarter Plugin architecture to invoke tools, retrieve data from private systems, access external APIs, execute code, and integrate other runtime capabilities. ";
  return (
    <>
      <section className="mt-5 mb-5 container" id="prompt-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={providerTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
