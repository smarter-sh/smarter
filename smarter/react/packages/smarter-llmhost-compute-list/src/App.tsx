/**
 *
 * Smarter LLMHost Compute List React App.
 * Used to display a list of the LLMHostComputes available to the user: the kinds of node,
 * and node groups, that their LLMHosts can run on.
 *
 */
import { gettext, TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { LLMHostCompute, LLMHostComputeListViewProps, LLMHostComputeDetailViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import DetailView from "@/components/DetailView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: gettext("Your LLMHost Compute") },
  { key: "shared" as TabKey, label: gettext("Shared LLMHost Compute") },
];

// Set the TabbedViewContext generic object type to LLMHostCompute,
// then omit the two abstract attributes ListView and DetailView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type LLMHostComputeTabbedViewContext = Omit<TabbedViewContext<LLMHostCompute>, "ListView" | "DetailView"> & {
  ListView: React.ComponentType<LLMHostComputeListViewProps>;
  DetailView: React.ComponentType<LLMHostComputeDetailViewProps>;
};

const llmhostComputeTabbedListViewContext: LLMHostComputeTabbedViewContext = {
  objectType: {} as LLMHostCompute,
  objectTypeName: "llmhostcompute",
  tabs: tabs,
  ListView: ListView,
  DetailView: DetailView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = gettext("LLM Host Compute");
  const icon = "ki-technology-2";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-llmhost.html";
  const helpText = gettext(
    "LLMHostCompute defines the kinds of server that LLMHosts run on, e.g. an AWS g6.2xlarge with one NVIDIA L4 GPU. Each one is an EKS managed node group, which Smarter creates when an LLMHost first needs one of its servers, and to which it adds and removes servers as LLMHosts are deployed and destroyed.",
  );
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
