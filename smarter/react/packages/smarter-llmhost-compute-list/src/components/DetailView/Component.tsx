/**
 * DetailView React Component
 *
 * The Details tab of an LLMHostCompute's detail, which the list opens when one of its rows is chosen (see
 * TabbedListView and ResourceDetail in @smarter/common): the compute's description, the status of its node group
 * and its actions, then the kind of node, the node group as of its last reconcile, and the metadata that every
 * resource has.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (LLMHostCompute): The LLMHostCompute.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={compute} onRequery={onRequery} filtering={filtering} />
 */
import { DetailField, DetailOverview, DetailSection, gettext, ResourceMetadataSection } from "@smarter/common";

import type { LLMHostComputeDetailViewProps } from "@/lib/Types";
import { formatGpus, formatPrice } from "@/lib/format";
import { StatusBar } from "@/components/StatusBar";
import { Toolbar } from "@/components/Toolbar";

function DetailView({ sessionContext, object: compute, onRequery, filtering }: LLMHostComputeDetailViewProps) {
  return (
    <>
      <DetailOverview description={compute.description}>
        <StatusBar compute={compute} />
        <Toolbar sessionContext={sessionContext} compute={compute} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Node")} icon="cpu">
        <DetailField
          label={gettext("Instance type")}
          value={compute.instanceType}
          type="code"
          help={gettext("The cloud's kind of node, e.g. g6.2xlarge.")}
        />
        <DetailField label={gettext("GPUs")} value={formatGpus(compute)} />
        <DetailField label={gettext("vCPUs")} value={compute.cpu} type="number" />
        <DetailField label={gettext("Memory (GiB)")} value={compute.memoryGb} type="number" />
        <DetailField
          label={gettext("Price per node")}
          value={compute.pricePerHour === null ? null : formatPrice(compute)}
          help={gettext("The cost per hour of one node. The LLMHosts that run on it share it.")}
        />
      </DetailSection>

      <DetailSection title={gettext("Node group")} icon="abstract-26">
        <DetailField
          label={gettext("Name")}
          value={compute.nodegroupName}
          type="code"
          help={gettext(
            "The cloud's name of the node group, which Smarter scales as LLMHosts are launched and destroyed.",
          )}
        />
        <DetailField
          label={gettext("Status")}
          value={compute.nodegroupStatus === "absent" ? gettext("Not created yet") : compute.nodegroupStatus}
          help={gettext(
            "As the cloud reports it. Smarter creates the node group when an LLMHost first needs one of its nodes.",
          )}
        />
        <DetailField label={gettext("Ready nodes")} value={compute.readyNodes} type="number" />
        <DetailField label={gettext("Desired nodes")} value={compute.desiredNodes} type="number" />
        <DetailField
          label={gettext("Maximum nodes")}
          value={compute.maxNodes}
          type="number"
          help={gettext("The most nodes that Smarter adds to the node group.")}
        />
        <DetailField
          label={gettext("LLMHosts")}
          value={compute.llmhostCount}
          type="number"
          help={gettext("The LLMHosts that run on it.")}
        />
        <DetailField label={gettext("Last reconciled")} value={compute.lastReconciledAt} type="dateTime" />
        <DetailField label={gettext("Status message")} value={compute.statusMessage} wide />
      </DetailSection>

      <ResourceMetadataSection resource={compute} filtering={filtering}>
        <DetailField label={gettext("Ready")} value={compute.ready} type="bool" />
        <DetailField label={gettext("RFC 1034 compliant name")} value={compute.rfc1034CompliantName} type="code" />
      </ResourceMetadataSection>
    </>
  );
}

export default DetailView;
