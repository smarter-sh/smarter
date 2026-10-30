/**
 *
 * Smarter MCPClient List React App.
 * Used to display a list of available mcpclients.
 *
 */
import { gettext, TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { MCPClient, MCPClientListViewProps, MCPClientDetailViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import DetailView from "@/components/DetailView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: gettext("Your MCPClients") },
  { key: "shared" as TabKey, label: gettext("Shared MCPClients") },
];

// Set the TabbedViewContext generic object type to MCPClient,
// then omit the two abstract attributes ListView and DetailView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type MCPClientTabbedViewContext = Omit<TabbedViewContext<MCPClient>, "ListView" | "DetailView"> & {
  ListView: React.ComponentType<MCPClientListViewProps>;
  DetailView: React.ComponentType<MCPClientDetailViewProps>;
};

const mcpclientTabbedListViewContext: MCPClientTabbedViewContext = {
  objectType: {} as MCPClient,
  objectTypeName: "mcpclient",
  tabs: tabs,
  ListView: ListView,
  DetailView: DetailView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = gettext("MCP (Model Context Protocol) Clients");
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-mcpclient.html";
  const helpText = gettext(
    "MCP Clients provide a standardized interface for connecting large language models to external tools and services through the Model Context Protocol (MCP).",
  );
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
