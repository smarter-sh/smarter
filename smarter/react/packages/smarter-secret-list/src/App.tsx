/**
 *
 * Smarter Secret List React App.
 * Used to display a list of available secrets.
 *
 */
import { TabbedListView } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { Secret, SecretListViewProps, SecretCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Secrets" },
  { key: "shared" as TabKey, label: "Shared Secrets" },
];

// Set the TabbedViewContext generic object type to Secret,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type SecretTabbedViewContext = Omit<
  TabbedViewContext<Secret>,
  "ListView" | "CardView"
> & {
  ListView: React.ComponentType<SecretListViewProps>;
  CardView: React.ComponentType<SecretCardViewProps>;
};

const secretTabbedListViewContext: SecretTabbedViewContext = {
  objectType: {} as Secret,
  objectTypeName: "secret",
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
      <section className="mt-5 mb-5 container" id="secret-list">
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={secretTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
