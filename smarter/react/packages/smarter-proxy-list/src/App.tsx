/**
 *
 * Smarter Proxy List React App.
 * Used to display a list of available proxies.
 *
 */
import { TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { Proxy, ProxyListViewProps, ProxyCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Proxies" },
  { key: "shared" as TabKey, label: "Shared Proxies" },
];

// Set the TabbedViewContext generic object type to Proxy,
// then omit the two abstract attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type ProxyTabbedViewContext = Omit<
  TabbedViewContext<Proxy>,
  "ListView" | "CardView"
> & {
  ListView: React.ComponentType<ProxyListViewProps>;
  CardView: React.ComponentType<ProxyCardViewProps>;
};

const proxyTabbedListViewContext: ProxyTabbedViewContext = {
  objectType: {} as Proxy,
  objectTypeName: "proxy",
  tabs: tabs,
  ListView: ListView,
  CardView: CardView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = "Proxies";
  const icon = "ki-data";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-proxy.html";
  const helpText =
    "A Proxy gives passthrough access to an LLM provider's API, e.g. OpenAI's or Anthropic's, with an API key that Smarter keeps as a Secret. Use the provider's own SDK, with the Proxy's URL as its base URL and a Smarter API key in place of the provider's: requests and responses pass through unchanged, the provider's API key is never exposed, and token usage is charged to your account.";
  return (
    <>
      <section className="mt-5 mb-5 container" id="proxy-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={proxyTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
