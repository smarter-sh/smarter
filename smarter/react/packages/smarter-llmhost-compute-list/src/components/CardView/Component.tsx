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

import "./styles.css";

function CardView({ sessionContext, objects, onRequery }: LLMHostComputeCardViewProps) {
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
                    {renderDetailRow("ID", compute.id, "number")}
                    {renderDetailRow("Description", compute.description)}
                    {renderDetailRow("Instance Type", compute.instanceType)}
                    {renderDetailRow("GPUs", formatGpus(compute))}
                    {renderDetailRow("CPU and Memory", formatCpuMemory(compute))}
                    {renderDetailRow("Price per Node", formatPrice(compute))}
                    {renderDetailRow("Node Group", compute.nodegroupName)}
                    {renderDetailRow("Node Group Status", compute.nodegroupStatus)}
                    {renderDetailRow("Nodes", formatNodes(compute))}
                    {renderDetailRow("Status Message", compute.statusMessage)}
                    {renderDetailRow("Last Reconciled", compute.lastReconciledAt, "dateTime")}
                    {renderDetailRow("LLMHosts", compute.llmhostCount, "number")}
                    {renderDetailRow("Manifest URL", compute.manifestUrl, "url")}
                    {renderDetailRow("Owner", compute.userProfile?.user?.username)}
                    {renderDetailRow("Owner Email", compute.userProfile?.user?.email)}
                    {renderDetailRow("Account Number", compute.userProfile?.account?.accountNumber)}
                    {renderDetailRow("Created", compute.createdAt, "dateTime")}
                    {renderDetailRow("Last Updated", compute.updatedAt, "dateTime")}
                    {renderDetailRow("Version", compute.version)}
                    {renderDetailRow("Tags", compute.tags, "str[]")}
                    {renderDetailRow("Annotations", compute.annotations, "json")}
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
