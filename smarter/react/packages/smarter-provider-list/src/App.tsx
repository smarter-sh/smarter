/**
 *
 * Smarter Provider List React App.
 * Used to display a list of available providers.
 *
 */
import { TabbedListView } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { Provider, ProviderListViewProps, ProviderCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Providers" },
  { key: "shared" as TabKey, label: "Shared Providers" },
];

// Set the TabbedViewContext generic object type to Provider,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type ProviderTabbedViewContext = Omit<
  TabbedViewContext<Provider>,
  "ListView" | "CardView"
> & {
  ListView: React.ComponentType<ProviderListViewProps>;
  CardView: React.ComponentType<ProviderCardViewProps>;
};

const providerTabbedListViewContext: ProviderTabbedViewContext = {
  objectType: {} as Provider,
  objectTypeName: "provider",
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
      <section className="mt-5 mb-5 container" id="provider-list">
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={providerTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
