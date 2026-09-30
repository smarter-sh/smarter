/**
 *
 * Smarter MCPClient List React App.
 * Used to display a list of available mcpclients.
 *
 */
import { TabbedListView, WorkbenchHelp } from "@smarter/common";
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
  const title = "MCP (Model Context Protocol) Clients";
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-mcpclient.html";
  const helpText = "MCP Clients provide a standardized interface for connecting large language models to external tools and services through the Model Context Protocol (MCP).";
  return (
    <>
      <section className="mt-5 mb-5 container" id="mcpclient-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={mcpclientTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
