/**
 *
 * StatusBar React component for displaying the state of an LLMHostCompute's node group, as of its
 * last reconcile: whether it exists, whether its nodes are ready, and whether LLMHosts use it.
 *
 * Exports:
 *   - StatusBar: Functional component that takes an LLMHostCompute and renders its status indicators.
 *
 * Usage:
 *   <StatusBar compute={compute} />
 */
import type { LLMHostCompute } from "@/lib/Types";
import { formatNodes } from "@/lib/format";

interface StatusbarProps {
  compute: LLMHostCompute;
}

/** The node group's status icon and its explanation. */
function nodeGroupIndicator(compute: LLMHostCompute): { icon: string; title: string } {
  const message = compute.statusMessage ? ` ${compute.statusMessage}` : "";
  switch (compute.nodegroupStatus) {
    case "absent":
      return {
        icon: "bi bi-cloud text-secondary",
        title: "No node group yet: Smarter creates it when an LLMHost first needs one of its nodes.",
      };
    case "ACTIVE":
      return { icon: "bi bi-cloud-check text-success", title: `Node group ${compute.nodegroupName} is active.${message}` };
    case "CREATING":
    case "UPDATING":
      return {
        icon: "bi bi-cloud-arrow-up text-primary",
        title: `Node group ${compute.nodegroupName} is ${compute.nodegroupStatus.toLowerCase()}.${message}`,
      };
    case "DELETING":
      return { icon: "bi bi-cloud-minus text-warning", title: `Node group ${compute.nodegroupName} is being deleted.` };
    default:
      return {
        icon: "bi bi-cloud-slash text-danger",
        title: `Node group ${compute.nodegroupName} is ${compute.nodegroupStatus}.${message}`,
      };
  }
}

export const StatusBar = ({ compute }: StatusbarProps) => {
  const nodeGroup = nodeGroupIndicator(compute);
  const starting = compute.readyNodes < compute.desiredNodes;
  return (
    <div className="statusbar d-flex align-items-center gap-2">
      {/* Node group */}
      <span className="status-icon" title={nodeGroup.title}>
        <i className={nodeGroup.icon} />
      </span>
      {/* Nodes */}
      <span
        className="status-icon"
        title={starting ? `Nodes: ${formatNodes(compute)}. Nodes are starting.` : `Nodes: ${formatNodes(compute)}`}
      >
        <i className={starting ? "bi bi-hourglass-split text-primary" : "bi bi-hdd-stack"} />{" "}
        <small>
          {compute.readyNodes}/{compute.desiredNodes}
        </small>
      </span>
      {/* LLMHosts */}
      <span className="status-icon" title={`LLMHosts that run on it: ${compute.llmhostCount}`}>
        <i className={compute.llmhostCount ? "bi bi-cpu text-info" : "bi bi-cpu text-secondary"} />{" "}
        <small>{compute.llmhostCount}</small>
      </span>
    </div>
  );
};
