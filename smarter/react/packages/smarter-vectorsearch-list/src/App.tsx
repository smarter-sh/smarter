/**
 *
 * Smarter Vectorsearch List React App.
 * Used to display a list of available vectorsearchs.
 *
 */
import { gettext, TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { Vectorsearch, VectorsearchListViewProps, VectorsearchDetailViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import DetailView from "@/components/DetailView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: gettext("Your Vectorsearch") },
  { key: "shared" as TabKey, label: gettext("Shared Vectorsearch") },
];

// Set the TabbedViewContext generic object type to Vectorsearch,
// then omit the two abstract attributes ListView and DetailView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type VectorsearchTabbedViewContext = Omit<TabbedViewContext<Vectorsearch>, "ListView" | "DetailView"> & {
  ListView: React.ComponentType<VectorsearchListViewProps>;
  DetailView: React.ComponentType<VectorsearchDetailViewProps>;
};

const vectorsearchTabbedListViewContext: VectorsearchTabbedViewContext = {
  objectType: {} as Vectorsearch,
  objectTypeName: "vectorsearch",
  tabs: tabs,
  ListView: ListView,
  DetailView: DetailView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = gettext("Vector Search");
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-vectorsearch.html";
  const helpText = gettext(
    "Smarter Vectorsearch provides a framework for executing RAG (Retrieval Augmented Generation) semantic search queries against locally-hosted vector databases managed by Smarter Vectorstore.",
  );
  return (
    <>
      <section className="mt-5 mb-5 container" id="vectorsearch-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={vectorsearchTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
