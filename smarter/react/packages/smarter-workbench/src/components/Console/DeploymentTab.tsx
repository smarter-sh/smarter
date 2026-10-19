/**
 * The Console's "Deployment" tab: what comes after deploying the LLMClient, the web console's deployment page, in
 * its workbench mode. It fetches the page's data when it is first opened, and manages the LLMClient's api key in
 * place, with the workbench's session.
 */
import { Loading } from "@smarter/common";
import { DeploymentPage } from "@smarter/llmclient-deployment";

import TabError from "@/components/Console/TabError";
import { useTabData } from "@/components/Console/useTabData";
import { fetchDeploymentPage } from "@/lib/api";
import type { WorkbenchConfig } from "@/lib/types";

function DeploymentTab({ workbench }: { workbench: WorkbenchConfig }) {
  const { data: page, error } = useTabData(() => fetchDeploymentPage(workbench.deploymentUrl ?? ""));
  if (error) return <TabError error={error} />;
  if (page === null) return <Loading />;
  return (
    <div className="console-deployment-page">
      <DeploymentPage context={{ page, session: workbench.session }} />
    </div>
  );
}

export default DeploymentTab;
