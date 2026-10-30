/**
 *
 * Smarter Connection List React App.
 * Used to display a list of available connections.
 *
 */
import { gettext, TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { Connection, ConnectionListViewProps, ConnectionDetailViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import DetailView from "@/components/DetailView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: gettext("Your Connections") },
  { key: "shared" as TabKey, label: gettext("Shared Connections") },
];

// Set the TabbedViewContext generic object type to Connection,
// then omit the two abstract attributes ListView and DetailView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type ConnectionTabbedViewContext = Omit<TabbedViewContext<Connection>, "ListView" | "DetailView"> & {
  ListView: React.ComponentType<ConnectionListViewProps>;
  DetailView: React.ComponentType<ConnectionDetailViewProps>;
};

const connectionTabbedListViewContext: ConnectionTabbedViewContext = {
  objectType: {} as Connection,
  objectTypeName: "connection",
  tabs: tabs,
  ListView: ListView,
  DetailView: DetailView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = gettext("Connections");
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-connection.html";
  const helpText = gettext(
    "A Connection defines and stores the credentials and configuration needed to access an external system, such as a database, REST API, Web service or email server, on which an AI application needs to communicate",
  );
  return (
    <>
      <section className="mt-5 mb-5 container" id="connection-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={connectionTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
