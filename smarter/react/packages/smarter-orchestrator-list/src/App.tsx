/**
 *
 * Smarter Orchestrator List React App.
 * Used to display a list of available orchestrators.
 *
 */
import { TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { Orchestrator, OrchestratorListViewProps, OrchestratorCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Orchestrators" },
  { key: "shared" as TabKey, label: "Shared Orchestrators" },
];

// Set the TabbedViewContext generic object type to Orchestrator,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type OrchestratorTabbedViewContext = Omit<
  TabbedViewContext<Orchestrator>,
  "ListView" | "CardView"
> & {
  ListView: React.ComponentType<OrchestratorListViewProps>;
  CardView: React.ComponentType<OrchestratorCardViewProps>;
};

const orchestratorTabbedListViewContext: OrchestratorTabbedViewContext = {
  objectType: {} as Orchestrator,
  objectTypeName: "orchestrator",
  tabs: tabs,
  ListView: ListView,
  CardView: CardView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = "Orchestrators";
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-orchestrator.html";
  const helpText = "Orchestrators are a standardized interface for coordinating multiple LLMClients (ie 'Harnesses') toward a shared agentic objective. Rather than hard-coding the control flow for each multi-model workflow, the Orchestrator lets you declare which LLMClients participate, what role each one plays, and which coordination strategy governs their interaction: sequential hand-offs, parallel fan-out, a supervisor delegating to workers, a router dispatching by intent, or a voting/debate pattern for consensus.";
  return (
    <>
      <section className="mt-5 mb-5 container" id="orchestrator-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={orchestratorTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
