/**
 *
 * Smarter Connection List React App.
 * Used to display a list of available connections.
 *
 */
import { TabbedListView } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { Connection, ConnectionListViewProps, ConnectionCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Connections" },
  { key: "shared" as TabKey, label: "Shared Connections" },
];

// Set the TabbedViewContext generic object type to Connection,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type ConnectionTabbedViewContext = Omit<
  TabbedViewContext<Connection>,
  "ListView" | "CardView"
> & {
  ListView: React.ComponentType<ConnectionListViewProps>;
  CardView: React.ComponentType<ConnectionCardViewProps>;
};

const connectionTabbedListViewContext: ConnectionTabbedViewContext = {
  objectType: {} as Connection,
  objectTypeName: "connection",
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
      <section className="mt-5 mb-5 container" id="connection-list">
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={connectionTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
