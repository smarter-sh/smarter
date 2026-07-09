/**
 *
 * Smarter Guardrail List React App.
 * Used to display a list of available guardrails.
 *
 */
import { TabbedListView, WorkbenchHelp } from "@smarter/common";
import type { SessionContext, TabbedViewContext, TabKey, Tabs } from "@smarter/common";

import type { Guardrail, GuardrailListViewProps, GuardrailCardViewProps } from "@/lib/Types";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";

const tabs: Tabs = [
  { key: "owned" as TabKey, label: "Your Guardrails" },
  { key: "shared" as TabKey, label: "Shared Guardrails" },
];

// Set the TabbedViewContext generic object type to Guardrail,
// then omit the two abstrasct attributes ListView and CardView
// from TabbedViewContext and replace these with
// concrete React component types from this package.
export type GuardrailTabbedViewContext = Omit<
  TabbedViewContext<Guardrail>,
  "ListView" | "CardView"
> & {
  ListView: React.ComponentType<GuardrailListViewProps>;
  CardView: React.ComponentType<GuardrailCardViewProps>;
};

const guardrailTabbedListViewContext: GuardrailTabbedViewContext = {
  objectType: {} as Guardrail,
  objectTypeName: "guardrail",
  tabs: tabs,
  ListView: ListView,
  CardView: CardView,
};

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = "Guardrails";
  const icon = "ki-book-open";
  const docsUrl = "https://docs.smarter.sh/smarter-resources/smarter-guardrail.html";
  const helpText = "Guardrails are responsible for enforcing constraints on the interaction between an application and a large language model. Rather than relying solely on prompt instructions such as 'do not reveal sensitive information' or 'respond only in JSON,' guardrails validate inputs, outputs, and execution state before information is accepted or returned. They may sanitize user input, reject prompt injection attempts, enforce schema validation, filter unsafe or out-of-scope responses, verify citations, limit tool access, or require structured output that conforms to predefined contracts.";
  return (
    <>
      <section className="mt-5 mb-5 container" id="guardrail-list">
        <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={guardrailTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
