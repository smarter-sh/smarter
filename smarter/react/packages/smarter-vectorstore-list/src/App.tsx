/**
 *
 * Smarter Vectorestore List React App.
 * Used to display a list of available vectorstores.
 *
 */
import { TabbedListView } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { Vectorestore, VectorestoreListViewProps, VectorestoreCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Vectorestores" },
  { key: "shared" as TabKey, label: "Shared Vectorestores" },
];

// Set the TabbedViewContext generic object type to Vectorestore,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type VectorestoreTabbedViewContext = Omit<
  TabbedViewContext<Vectorestore>,
  "ListView" | "CardView"
> & {
  ListView: React.ComponentType<VectorestoreListViewProps>;
  CardView: React.ComponentType<VectorestoreCardViewProps>;
};

const vectorstoreTabbedListViewContext: VectorestoreTabbedViewContext = {
  objectType: {} as Vectorestore,
  objectTypeName: "vectorstore",
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
      <section className="mt-5 mb-5 container" id="vectorstore-list">
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={vectorstoreTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
