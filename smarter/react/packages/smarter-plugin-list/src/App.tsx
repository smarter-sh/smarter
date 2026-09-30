/**
 *
 * Smarter Plugin List React App.
 * Used to display a list of available plugins.
 *
 */
import { TabbedListView, WorkbenchHelp } from "@smarter/common";
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
export type PluginTabbedViewContext = Omit<TabbedViewContext<Plugin>, "ListView" | "CardView"> & {
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
  const title = "Plugins";
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-plugin.html";
  const helpText =
    "Plugins provide a declarative yaml manifest alternative to programming in Python in order to extend LLM tool functionality. Plugins are fundamentally more feature rich than traditional LLM function tools. A Smarter Plugin manifest defines not only what proprietary data is being made available to the LLM, but also the LLM prompt specification itself (which provider, model, temperature, etc.), and most importantly, the criteria which the tool should be presented to the LLM. Plugins connect directly to remote data sources — SQL databases, REST APIs, free-form JSON endpoints, and Anthropic-standard SKILL.md files — giving the LLM live access to proprietary data and capabilities without writing custom integration code.";
  return (
    <>
      <section className="mt-5 mb-5 container" id="plugin-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={pluginTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
