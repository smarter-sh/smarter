/**
 *
 * Smarter LLMHost List React App.
 * Used to display a list of available llmhosts.
 *
 */
import { TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { LLMHost, LLMHostListViewProps, LLMHostCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your LLMHosts" },
  { key: "shared" as TabKey, label: "Shared LLMHosts" },
];

// Set the TabbedViewContext generic object type to LLMHost,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type LLMHostTabbedViewContext = Omit<
  TabbedViewContext<LLMHost>,
  "ListView" | "CardView"
> & {
  ListView: React.ComponentType<LLMHostListViewProps>;
  CardView: React.ComponentType<LLMHostCardViewProps>;
};

const llmhostTabbedListViewContext: LLMHostTabbedViewContext = {
  objectType: {} as LLMHost,
  objectTypeName: "llmhost",
  tabs: tabs,
  ListView: ListView,
  CardView: CardView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = "LLM Hosts";
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-llmhost.html";
  const helpText = "LLMHosts provide a standardized interface for deploying and managing self-hosted large language models from platforms like HuggingFace within Smarter-orchestrated applications.";
  return (
    <>
      <section className="mt-5 mb-5 container" id="llmhost-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={llmhostTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
