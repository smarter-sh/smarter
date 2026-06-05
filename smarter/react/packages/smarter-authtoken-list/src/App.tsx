/**
 *
 * Smarter AuthToken List React App.
 * Used to display a list of available authtokens.
 *
 */
import { TabbedListView } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";
import type { AuthToken, AuthTokenListViewProps, AuthTokenCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your AuthTokens" },
  { key: "shared" as TabKey, label: "Shared AuthTokens" },
];

// Set the TabbedViewContext generic object type to AuthToken,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type AuthTokenTabbedViewContext = Omit<
  TabbedViewContext<AuthToken>,
  "ListView" | "CardView"
> & {
  ListView: React.ComponentType<AuthTokenListViewProps>;
  CardView: React.ComponentType<AuthTokenCardViewProps>;
};

const authtokenTabbedListViewContext: AuthTokenTabbedViewContext = {
  objectType: {} as AuthToken,
  objectTypeName: "authtoken",
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
      <section className="mt-5 mb-5 container" id="authtoken-list">
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={authtokenTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
