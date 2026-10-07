/**
 *
 * Smarter Vectorstore List React App.
 * Used to display a list of available vectorstores.
 *
 */
import { TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { Vectorstore, VectorstoreListViewProps, VectorstoreCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Vectorstores" },
  { key: "shared" as TabKey, label: "Shared Vectorstores" },
];

// Set the TabbedViewContext generic object type to Vectorstore,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type VectorstoreTabbedViewContext = Omit<TabbedViewContext<Vectorstore>, "ListView" | "CardView"> & {
  ListView: React.ComponentType<VectorstoreListViewProps>;
  CardView: React.ComponentType<VectorstoreCardViewProps>;
};

const vectorstoreTabbedListViewContext: VectorstoreTabbedViewContext = {
  objectType: {} as Vectorstore,
  objectTypeName: "vectorstore",
  tabs: tabs,
  ListView: ListView,
  CardView: CardView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = "Vectorstores";
  const icon = "ki-data";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-vectorstore.html";
  const helpText =
    "A Vectorstore is a vector database for retrieval-augmented generation (RAG): documents, such as PDFs, are split into chunks, embedded, and loaded into it, and searched by meaning. Smarter runs Qdrant on its own Kubernetes cluster, or connects to Pinecone or Qdrant Cloud. It creates and destroys the database, loads and removes documents, and takes scheduled snapshots. Create one with a Vectorstore manifest.";
  return (
    <>
      <section className="mt-5 mb-5 container" id="vectorstore-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={vectorstoreTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
