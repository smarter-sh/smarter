/**
 *
 * Smarter Guardrail List React App.
 * Used to display a list of available guardrails.
 *
 */
import { TabbedListView } from "@smarter/common";
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
  return (
    <>
      <section className="mt-5 mb-5 container" id="guardrail-list">
        <TabbedListView sessionContext={sessionContext} tabbedListViewContext={guardrailTabbedListViewContext} />
      </section>
    </>
  );
}

export default App;
