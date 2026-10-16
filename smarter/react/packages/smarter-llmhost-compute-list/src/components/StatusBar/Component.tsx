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
import { gettext, interpolate } from "@smarter/common";

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
        title: gettext("No node group yet: Smarter creates it when an LLMHost first needs one of its nodes."),
      };
    case "ACTIVE":
      return {
        icon: "bi bi-cloud-check text-success",
        title: interpolate(gettext("Node group %(nodegroupName)s is active.%(message)s"), {
          nodegroupName: compute.nodegroupName,
          message,
        }),
      };
    case "CREATING":
    case "UPDATING":
      return {
        icon: "bi bi-cloud-arrow-up text-primary",
        title: interpolate(gettext("Node group %(nodegroupName)s is %(nodegroupStatus)s.%(message)s"), {
          nodegroupName: compute.nodegroupName,
          nodegroupStatus: compute.nodegroupStatus.toLowerCase(),
          message,
        }),
      };
    case "DELETING":
      return {
        icon: "bi bi-cloud-minus text-warning",
        title: interpolate(gettext("Node group %(nodegroupName)s is being deleted."), {
          nodegroupName: compute.nodegroupName,
        }),
      };
    default:
      return {
        icon: "bi bi-cloud-slash text-danger",
        title: interpolate(gettext("Node group %(nodegroupName)s is %(nodegroupStatus)s.%(message)s"), {
          nodegroupName: compute.nodegroupName,
          nodegroupStatus: compute.nodegroupStatus,
          message,
        }),
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
        title={
          starting
            ? interpolate(gettext("Nodes: %(nodes)s. Nodes are starting."), { nodes: formatNodes(compute) })
            : interpolate(gettext("Nodes: %(nodes)s"), { nodes: formatNodes(compute) })
        }
      >
        <i className={starting ? "bi bi-hourglass-split text-primary" : "bi bi-hdd-stack"} />{" "}
        <small>
          {compute.readyNodes}/{compute.desiredNodes}
        </small>
      </span>
      {/* LLMHosts */}
      <span
        className="status-icon"
        title={interpolate(gettext("LLMHosts that run on it: %(llmhostCount)s"), {
          llmhostCount: compute.llmhostCount,
        })}
      >
        <i className={compute.llmhostCount ? "bi bi-cpu text-info" : "bi bi-cpu text-secondary"} />{" "}
        <small>{compute.llmhostCount}</small>
      </span>
    </div>
  );
};
