/**
 * Plugin List
 * Used to display a list of available plugins.
 *
 */
import { TabbedListView } from "@smarter/common";
import type { SessionContext } from "@smarter/common";
import type { PluginTabbedViewContext, Plugin } from "@/lib/Types";
import ListView from "@/components/ListView"
import CardView from "@/components/CardView"

const pluginTabbedViewContext: PluginTabbedViewContext = {
  objectType: {} as Plugin,
  objectTypeName: "plugin",
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
        <TabbedListView sessionContext={sessionContext} tabbedViewContext={pluginTabbedViewContext} />
      </section>
    </>
  );
}

export default App;
