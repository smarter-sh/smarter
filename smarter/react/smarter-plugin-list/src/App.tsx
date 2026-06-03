/**
 * Plugin List
 * Used to display a list of available plugins.
 *
 */
import { TabbedListView } from "@smarter/common";
import type { SessionContext, TabKey, Tabs } from "@smarter/common";
import type { PluginTabbedViewContext, Plugin } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Plugins" },
  { key: "shared" as TabKey, label: "Shared Plugins" },
];

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
