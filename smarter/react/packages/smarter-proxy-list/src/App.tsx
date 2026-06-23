/**
 *
 * Smarter Proxy List React App.
 * Used to display a list of available proxies.
 *
 */
import { TabbedListView } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { Proxy, ProxyListViewProps, ProxyCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Proxies" },
  { key: "shared" as TabKey, label: "Shared Proxies" },
];

// Set the TabbedViewContext generic object type to Proxy,
// then omit the two abstrasct attributes ListView and CardView
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
  return (
    <>
      <section className="mt-5 mb-5 container" id="proxy-list">
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={proxyTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
