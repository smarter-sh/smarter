/**
 *
 * Smarter Vectorstore List React App.
 * Used to display a list of available vectorstores.
 *
 */
import { gettext, TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { Vectorstore, VectorstoreListViewProps, VectorstoreDetailViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import DetailView from "@/components/DetailView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: gettext("Your Vectorstores") },
  { key: "shared" as TabKey, label: gettext("Shared Vectorstores") },
];

// Set the TabbedViewContext generic object type to Vectorstore,
// then omit the two abstract attributes ListView and DetailView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type VectorstoreTabbedViewContext = Omit<TabbedViewContext<Vectorstore>, "ListView" | "DetailView"> & {
  ListView: React.ComponentType<VectorstoreListViewProps>;
  DetailView: React.ComponentType<VectorstoreDetailViewProps>;
};

const vectorstoreTabbedListViewContext: VectorstoreTabbedViewContext = {
  objectType: {} as Vectorstore,
  objectTypeName: "vectorstore",
  tabs: tabs,
  ListView: ListView,
  DetailView: DetailView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = gettext("Vectorstores");
  const icon = "ki-data";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-vectorstore.html";
  const helpText = gettext(
    "A Vectorstore is a vector database for retrieval-augmented generation (RAG): documents, such as PDFs, are split into chunks, embedded, and loaded into it, and searched by meaning. Smarter runs Qdrant on its own Kubernetes cluster, or connects to Pinecone or Qdrant Cloud. It creates and destroys the database, loads and removes documents, and takes scheduled snapshots. Create one with a Vectorstore manifest.",
  );
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
