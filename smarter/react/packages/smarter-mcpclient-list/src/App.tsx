/**
 *
 * Smarter MCPClient List React App.
 * Used to display a list of available mcpclients.
 *
 */
import { TabbedListView } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { MCPClient, MCPClientListViewProps, MCPClientCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your MCPClients" },
  { key: "shared" as TabKey, label: "Shared MCPClients" },
];

// Set the TabbedViewContext generic object type to MCPClient,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type MCPClientTabbedViewContext = Omit<
  TabbedViewContext<MCPClient>,
  "ListView" | "CardView"
> & {
  ListView: React.ComponentType<MCPClientListViewProps>;
  CardView: React.ComponentType<MCPClientCardViewProps>;
};

const mcpclientTabbedListViewContext: MCPClientTabbedViewContext = {
  objectType: {} as MCPClient,
  objectTypeName: "mcpclient",
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
      <section className="mt-5 mb-5 container" id="mcpclient-list">
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={mcpclientTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
