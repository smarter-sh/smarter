/**
 *
 * Smarter Custom Domain List React App.
 * Used to display a list of the custom domains of the llmclients available to the user.
 *
 */
import { TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { CustomDomain, CustomDomainListViewProps, CustomDomainCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Custom Domains" },
  { key: "shared" as TabKey, label: "Shared Custom Domains" },
];

// Set the TabbedViewContext generic object type to CustomDomain,
// then omit the two abstract attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type CustomDomainTabbedViewContext = Omit<TabbedViewContext<CustomDomain>, "ListView" | "CardView"> & {
  ListView: React.ComponentType<CustomDomainListViewProps>;
  CardView: React.ComponentType<CustomDomainCardViewProps>;
};

const customDomainTabbedListViewContext: CustomDomainTabbedViewContext = {
  objectType: {} as CustomDomain,
  objectTypeName: "custom domain",
  tabs: tabs,
  ListView: ListView,
  CardView: CardView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = "Custom Domains";
  const icon = "ki-arrow-circle-right";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-custom-domain.html";
  const helpText =
    "A Custom Domain serves an LLMClient from your own branded domain name, rather than from the platform's default domain. Like any other Smarter resource, a Custom Domain is defined and managed through a standard SAM manifest, and can be shared with your account. Deploying it registers the domain in an AWS Route53 hosted zone, and it is verified once you have added its NS records to your root domain's DNS settings. An LLMClient uses it with its spec.customDomain.";
  return (
    <>
      <section className="mt-5 mb-5 container" id="custom-domain-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={customDomainTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
