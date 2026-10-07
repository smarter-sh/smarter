/**
 *
 * Smarter LLMHost Compute List React App.
 * Used to display a list of the LLMHostComputes available to the user: the kinds of node,
 * and node groups, that their LLMHosts can run on.
 *
 */
import { TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { LLMHostCompute, LLMHostComputeListViewProps, LLMHostComputeCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your LLMHost Compute" },
  { key: "shared" as TabKey, label: "Shared LLMHost Compute" },
];

// Set the TabbedViewContext generic object type to LLMHostCompute,
// then omit the two abstract attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type LLMHostComputeTabbedViewContext = Omit<TabbedViewContext<LLMHostCompute>, "ListView" | "CardView"> & {
  ListView: React.ComponentType<LLMHostComputeListViewProps>;
  CardView: React.ComponentType<LLMHostComputeCardViewProps>;
};

const llmhostComputeTabbedListViewContext: LLMHostComputeTabbedViewContext = {
  objectType: {} as LLMHostCompute,
  objectTypeName: "llmhostcompute",
  tabs: tabs,
  ListView: ListView,
  CardView: CardView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = "LLM Host Compute";
  const icon = "ki-technology-2";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-llmhost.html";
  const helpText =
    "LLMHostCompute defines the kinds of server that LLMHosts run on, e.g. an AWS g6.2xlarge with one NVIDIA L4 GPU. Each one is an EKS managed node group, which Smarter creates when an LLMHost first needs one of its servers, and to which it adds and removes servers as LLMHosts are deployed and destroyed.";
  return (
    <>
      <section className="mt-5 mb-5 container" id="llmhost-compute-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={llmhostComputeTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
