/**
 *
 * Smarter LLMTool List React App.
 * Used to display the LLMTools available to the user: their own and shared Tool Plugins, and,
 * read-only, the Extensions that their account may use.
 *
 */
import { gettext, TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";
import type { LLMTool, LLMToolListViewProps, LLMToolDetailViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import DetailView from "@/components/DetailView";
import ExtensionListView from "@/components/ExtensionListView";
import ExtensionDetailView from "@/components/ExtensionDetailView";

// The Extensions tab is read-only for every user, superusers included: superusers manage
// extensions in the Extensions console. Its objects are Extensions, not LLMTools, so it has
// its own views, and its list api is <ApiUrl>extensions/.
const tabs: Tabs = [
  { key: "owned" as TabKey, label: gettext("Your Tool Plugins") },
  { key: "shared" as TabKey, label: gettext("Shared Tool Plugins") },
  {
    key: "extensions" as TabKey,
    label: gettext("Extensions"),
    objectTypeName: "Extension",
    ListView: ExtensionListView,
    DetailView: ExtensionDetailView,
  },
];

// Set the TabbedViewContext generic object type to LLMTool,
// then omit the two abstract attributes ListView and DetailView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type LLMToolTabbedViewContext = Omit<TabbedViewContext<LLMTool>, "ListView" | "DetailView"> & {
  ListView: React.ComponentType<LLMToolListViewProps>;
  DetailView: React.ComponentType<LLMToolDetailViewProps>;
};

const llmtoolTabbedListViewContext: LLMToolTabbedViewContext = {
  objectType: {} as LLMTool,
  objectTypeName: "LLMTool",
  tabs: tabs,
  ListView: ListView,
  DetailView: DetailView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = gettext("LLMTools");
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-framework/extensibility.html";
  const helpText = gettext(
    "LLMTools give an LLM what it was not trained on: live data, actions and calculations. The LLM decides for itself which tool it needs, Smarter runs it, and the LLM writes its answer from the result. Smarter offers the tools that an LLMClient lists, of three kinds. Tool Plugins are declarative: a prompt engineer writes a YAML manifest that configures one of Smarter's built-in tool patterns (answer from static data, run a SQL query, call a REST API, follow an Anthropic-standard SKILL.md, search the web, or search for images), with a selector that decides when it is offered. Plugins are owned by a user, shared within an account, and need no code. Extensions are code: Python packages, from the signed Smarter Extension registry or uploaded, whose tools do anything Python can do. A platform administrator installs and enables them, and decides which accounts may use them; the Extensions tab lists, read-only, those that your account may use. Note also that MCPClients perform a similar function: they connect to remote Model Context Protocol servers, such as GitHub's, and offer their tools; they have their own page. All three appear side by side in an LLMClient manifest, under spec.plugins, spec.extensions and spec.mcpClients.",
  );
  return (
    <>
      <section className="mt-5 mb-5 container" id="llmtool-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={llmtoolTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
