/**
 *
 * Smarter Vectorsearch List React App.
 * Used to display a list of available vectorsearchs.
 *
 */
import { TabbedListView } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { Vectorsearch, VectorsearchListViewProps, VectorsearchCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Vectorsearch" },
  { key: "shared" as TabKey, label: "Shared Vectorsearch" },
];

// Set the TabbedViewContext generic object type to Vectorsearch,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type VectorsearchTabbedViewContext = Omit<
  TabbedViewContext<Vectorsearch>,
  "ListView" | "CardView"
> & {
  ListView: React.ComponentType<VectorsearchListViewProps>;
  CardView: React.ComponentType<VectorsearchCardViewProps>;
};

const vectorsearchTabbedListViewContext: VectorsearchTabbedViewContext = {
  objectType: {} as Vectorsearch,
  objectTypeName: "vectorsearch",
  tabs: tabs,
  ListView: ListView,
  CardView: CardView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = "Plugins";
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-plugin.html";
  const helpText = "";
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
