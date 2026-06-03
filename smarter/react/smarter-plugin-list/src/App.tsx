/**
 * Plugin List
 * Used to display a list of available plugins.
 *
 */
import { TabbedListView } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";
import type { Plugin, PluginListViewProps, PluginCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Plugins" },
  { key: "shared" as TabKey, label: "Shared Plugins" },
];

// Set the TabbedViewContext generic object type to Plugin,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type PluginTabbedViewContext = Omit<
  TabbedViewContext<Plugin>,
  "ListView" | "CardView"
> & {
  ListView: React.ComponentType<PluginListViewProps>;
  CardView: React.ComponentType<PluginCardViewProps>;
};

const pluginTabbedListViewContext: PluginTabbedViewContext = {
  objectType: {} as Plugin,
  objectTypeName: "plugin",
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
      <section className="mt-5 mb-5 container" id="plugin-list">
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={pluginTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
