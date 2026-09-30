/**
 *
 * Smarter Provider List React App.
 * Used to display a list of available providers.
 *
 */
import { TabbedListView, WorkbenchHelp } from "@smarter/common";
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
  const title = "Providers";
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-provider.html";
  const helpText = "Providers connect third-party LLM providers to the Smarter Platform. Rather than wiring each provider in through manual, one-off configuration, it exposes a structured onboarding process that validates a provider's models before they become available to Smarter Resources. As part of that process, the app runs a battery of verification checks confirming that a provider's models are compatible with the Smarter Resource feature set, and it re-runs those checks periodically so compatibility doesn't silently drift over time.";
  return (
    <>
      <section className="mt-5 mb-5 container" id="provider-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={providerTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
