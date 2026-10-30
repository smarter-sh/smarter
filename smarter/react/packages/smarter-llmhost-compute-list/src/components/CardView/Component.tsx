/**
 * CardView React Component
 *
 * This component renders LLMHostCompute resources as individual cards, displaying the kind of node,
 * its node group's status, and actions for each LLMHostCompute.
 *
 * Features:
 * - Displays LLMHostCompute details in a visually distinct card format.
 * - Integrates action buttons for manifest, clone, rename, and delete operations.
 * - Uses a detail row renderer for flexible display of LLMHostCompute attributes.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - objects (LLMHostCompute[]): Array of LLMHostCompute objects to display.
 * - onRequery (function): Callback to refresh the data after an action.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} objects={computes} onRequery={onRequery} />
 */
import type { LLMHostComputeCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { formatCpuMemory, formatGpus, formatNodes, formatPrice } from "@/lib/format";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "@/components/CardView/styles.css";
import { AnnotationsRow, gettext, TagsRow } from "@smarter/common";

function CardView({ sessionContext, objects, onRequery, filtering }: LLMHostComputeCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((compute) => (
          <div className="col-12" key={compute.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} compute={compute} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar compute={compute} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={compute.manifestUrl} className="text-decoration-none text-primary">
                    {compute.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow(gettext("ID"), compute.id, "number")}
                    {renderDetailRow(gettext("Description"), compute.description)}
                    {renderDetailRow(gettext("Instance Type"), compute.instanceType)}
                    {renderDetailRow(gettext("GPUs"), formatGpus(compute))}
                    {renderDetailRow(gettext("CPU and Memory"), formatCpuMemory(compute))}
                    {renderDetailRow(gettext("Price per Node"), formatPrice(compute))}
                    {renderDetailRow(gettext("Node Group"), compute.nodegroupName)}
                    {renderDetailRow(gettext("Node Group Status"), compute.nodegroupStatus)}
                    {renderDetailRow(gettext("Nodes"), formatNodes(compute))}
                    {renderDetailRow(gettext("Status Message"), compute.statusMessage)}
                    {renderDetailRow(gettext("Last Reconciled"), compute.lastReconciledAt, "dateTime")}
                    {renderDetailRow(gettext("LLMHosts"), compute.llmhostCount, "number")}
                    {renderDetailRow(gettext("Manifest URL"), compute.manifestUrl, "url")}
                    {renderDetailRow(gettext("Owner"), compute.userProfile?.user?.username)}
                    {renderDetailRow(gettext("Owner Email"), compute.userProfile?.user?.email)}
                    {renderDetailRow(gettext("Account Number"), compute.userProfile?.account?.accountNumber)}
                    {renderDetailRow(gettext("Created"), compute.createdAt, "dateTime")}
                    {renderDetailRow(gettext("Last Updated"), compute.updatedAt, "dateTime")}
                    {renderDetailRow(gettext("Version"), compute.version)}
                    <TagsRow tags={compute.tags} filtering={filtering} />
                    <AnnotationsRow annotations={compute.annotations} filtering={filtering} />
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ))}
    </div>
  );
}

export default CardView;
