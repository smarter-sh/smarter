/**
 *
 * Smarter AuthToken List React App.
 * Used to display a list of available authtokens.
 *
 */
import { TabbedListView, WorkbenchHelp } from "@smarter/common";
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
  const title = "AuthTokens";
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-framework/developer-reference/lib/drf/models.html";
  const helpText = "Smarter Authtokens are a Django REST Framework API authentication token that can be associated with any Smarter resource, rather than being limited to a user account. This allows access to be scoped precisely: individual users and services can each be issued a token limited to a specific resource, rather than sharing one broad credential across an entire integration.";
  return (
    <>
      <section className="mt-5 mb-5 container" id="authtoken-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={authtokenTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
