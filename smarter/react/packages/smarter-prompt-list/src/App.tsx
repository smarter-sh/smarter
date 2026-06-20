/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import { TabbedListView } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";
import type { LLMClient, LLMClientListViewProps, LLMClientCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Prompts" },
  { key: "shared" as TabKey, label: "Shared Prompts" },
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
  objectTypeName: "provider",
  tabs: tabs,
  ListView: ListView,
  CardView: CardView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  return (
    <>
      <section className="mt-5 mb-5 container" id="prompt-list">
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={providerTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
