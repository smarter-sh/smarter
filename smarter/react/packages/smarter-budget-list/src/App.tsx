/**
 *
 * Smarter Budget List React App.
 * Used to display the budgets, and the budget versus actual spending of the resources they are attached to.
 *
 */
import { WorkbenchHelp } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import BudgetList from "@/components/BudgetList";

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = "Budgets";
  const icon = "ki-dollar";
  const docsUrl = "https://docs.smarter.sh/smarter-platform/cost-accounting.html";
  const helpText =
    "A Budget is a set of spending limits, in USD or in tokens, per hour, day, week or month, and in total. It is enforced on each of the resources it is attached to: users, accounts, LLMClients, Providers, Proxies, LLMHost computes, plugins and more. When a resource's spending reaches a limit, its requests are refused with the budget's message, for example in the chat window, until the billing period renews. Superusers manage budgets with Budget manifests.";
  return (
    <section className="mt-5 mb-5 container" id="budget-list">
      <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
      <BudgetList sessionContext={sessionContext} />
    </section>
  );
}

export default App;
