/**
 *
 * Smarter Infrastructure Resource List React App.
 * Used to display the ledger of the cloud resources that the platform has created and destroyed.
 *
 */
import { WorkbenchHelp } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import InfrastructureResourceList from "@/components/InfrastructureResourceList";

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  const title = "Infrastructure Resources";
  const icon = "ki-cloud";
  const docsUrl = "https://docs.smarter.sh/smarter-framework/technologies/infrastructure.html";
  const helpText =
    "The ledger of the cloud resources that the platform has created, whichever cloud provider created them: DNS zones and records, TLS certificates, and billable Kubernetes resources, such as volumes and load balancers. Billable resources cost money for as long as they exist. The platform records each resource when it creates or destroys it, so this list is read-only.";
  return (
    <section className="mt-5 mb-5 container" id="infrastructure-resource-list">
      <WorkbenchHelp title={title} icon={icon} docsUrl={docsUrl} helpText={helpText} />
      <InfrastructureResourceList sessionContext={sessionContext} />
    </section>
  );
}

export default App;
