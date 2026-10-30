/**
 * DetailView React Component
 *
 * The Details tab of an LLMHost's detail, which the list opens when one of its rows is chosen (see
 * TabbedListView and ResourceDetail in @smarter/common): the LLMHost's description, status and actions, then the
 * model that it serves, how it serves it, the compute that it runs on, its deployment as last observed, and the
 * metadata that every resource has.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (LLMHost): The LLMHost.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={llmhost} onRequery={onRequery} filtering={filtering} />
 */
import {
  DetailField,
  DetailOverview,
  DetailSection,
  gettext,
  interpolate,
  ResourceMetadataSection,
} from "@smarter/common";

import type { HostStatus, LLMHost, LLMHostDetailViewProps } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";

/** The badge of each lifecycle status of an LLMHost's deployment. */
const STATUS_BADGES: Record<HostStatus, { className: string; label: string }> = {
  provisioning: { className: "badge-light-warning", label: gettext("Provisioning") },
  pending: { className: "badge-light", label: gettext("Pending") },
  downloading: { className: "badge-light-warning", label: gettext("Downloading") },
  deploying: { className: "badge-light-warning", label: gettext("Deploying") },
  active: { className: "badge-light-success", label: gettext("Active") },
  degraded: { className: "badge-light-warning", label: gettext("Degraded") },
  inactive: { className: "badge-light", label: gettext("Inactive") },
  error: { className: "badge-light-danger", label: gettext("Error") },
};

/** What the model can do, of streaming, function calling, vision and reasoning. */
function capabilities(llmhost: LLMHost): string[] {
  return [
    llmhost.supportsStreaming && gettext("Streaming"),
    llmhost.supportsFunctionCalling && gettext("Function calling"),
    llmhost.supportsVision && gettext("Vision"),
    llmhost.supportsReasoning && gettext("Reasoning"),
  ].filter((capability): capability is string => Boolean(capability));
}

/** The cost per hour of one replica, e.g. "$0.98/hr". */
function formatCost(costPerHour: string | null): string | null {
  if (costPerHour === null || costPerHour === undefined || costPerHour === "") return null;
  return interpolate(gettext("$%(cost)s/hr"), { cost: Number(costPerHour).toFixed(2) });
}

function DetailView({ sessionContext, object: llmhost, onRequery, filtering }: LLMHostDetailViewProps) {
  const status = STATUS_BADGES[llmhost.status] ?? { className: "badge-light", label: llmhost.status };
  return (
    <>
      <DetailOverview description={llmhost.description}>
        <span className={`badge ${status.className} fw-semibold`} title={llmhost.statusMessage || undefined}>
          {status.label}
        </span>
        {!llmhost.isActive && <span className="badge badge-light fw-semibold">{gettext("Disabled")}</span>}
        <Toolbar sessionContext={sessionContext} llmhost={llmhost} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Model")} icon="abstract-26">
        <DetailField
          label={gettext("Repository")}
          value={llmhost.modelRepository}
          type="code"
          help={gettext("Where the weights are downloaded from, e.g. a HuggingFace repository.")}
        />
        <DetailField label={gettext("Source")} value={llmhost.modelSource} />
        <DetailField label={gettext("Revision")} value={llmhost.modelRevision} type="code" />
        <DetailField label={gettext("Task")} value={llmhost.modelTask} />
        <DetailField
          label={gettext("Served model name")}
          value={llmhost.servedModelName}
          type="code"
          help={gettext("The model name that clients send in their requests.")}
        />
        <DetailField label={gettext("Architecture")} value={llmhost.modelArchitecture} type="code" />
        <DetailField label={gettext("Parameters")} value={llmhost.parameterCount} type="number" />
        <DetailField
          label={gettext("Context window")}
          value={llmhost.contextWindow}
          type="number"
          help={gettext("The most tokens, of prompt and reply together, that the model accepts.")}
        />
        <DetailField
          label={gettext("Quantization")}
          value={llmhost.quantization}
          help={gettext("The numeric precision, or compression, of the model's weights.")}
        />
        <DetailField label={gettext("Embedding dimensions")} value={llmhost.embeddingDimensions} type="number" />
        <DetailField label={gettext("License")} value={llmhost.license} />
        <DetailField label={gettext("Capabilities")} value={capabilities(llmhost)} type="list" wide />
      </DetailSection>

      <DetailSection title={gettext("Serving")} icon="technology-2">
        <DetailField
          label={gettext("Inference engine")}
          value={llmhost.inferenceEngine}
          help={gettext("The server that loads the weights and answers requests, e.g. vLLM.")}
        />
        <DetailField
          label={gettext("API format")}
          value={llmhost.apiFormat}
          help={gettext("The protocol that its endpoint speaks, whatever its inference engine.")}
        />
        <DetailField
          label={gettext("API key secret")}
          value={llmhost.apiKeySecret}
          type="code"
          help={gettext("The ID of the Smarter Secret that holds its API key. The key itself is never shown.")}
        />
      </DetailSection>

      <DetailSection title={gettext("Compute")} icon="cpu">
        <DetailField
          label={gettext("LLMHostCompute")}
          value={llmhost.compute}
          type="code"
          help={gettext("The ID of the LLMHostCompute, the node group, that it runs on.")}
        />
        <DetailField label={gettext("GPU type")} value={llmhost.gpuType} />
        <DetailField label={gettext("GPUs")} value={llmhost.gpuCount} type="number" />
        <DetailField
          label={gettext("VRAM required (GB)")}
          value={llmhost.vramRequiredGb}
          type="number"
          help={gettext("The GPU memory that the model needs.")}
        />
        <DetailField label={gettext("Replicas")} value={llmhost.replicas} type="number" />
        <DetailField label={gettext("Ready replicas")} value={llmhost.readyReplicas} type="number" />
        <DetailField
          label={gettext("Cost per replica")}
          value={formatCost(llmhost.costPerHour)}
          help={gettext("The cost per hour of one replica: its share of its compute's node.")}
        />
      </DetailSection>

      <DetailSection title={gettext("Deployment")} icon="cloud">
        <DetailField label={gettext("Status")} value={status.label} />
        <DetailField label={gettext("Deployed")} value={llmhost.deployedAt} type="dateTime" />
        <DetailField
          label={gettext("Endpoint")}
          value={llmhost.endpointUrl}
          type="code"
          help={gettext("Its base URL inside the cluster.")}
        />
        <DetailField
          label={gettext("Public URL")}
          value={llmhost.publicUrl}
          type="url"
          help={gettext("Its base URL from outside the cluster, if it has an Ingress.")}
        />
        <DetailField label={gettext("Base URL")} value={llmhost.baseUrl} type="url" />
        <DetailField label={gettext("Health check")} value={llmhost.healthCheckUrl} type="code" />
        <DetailField label={gettext("Last health check")} value={llmhost.lastHealthCheckAt} type="dateTime" />
        <DetailField label={gettext("Healthy")} value={llmhost.lastHealthOk} type="bool" />
        <DetailField label={gettext("Status message")} value={llmhost.statusMessage} wide />
      </DetailSection>

      <ResourceMetadataSection resource={llmhost} filtering={filtering}>
        <DetailField label={gettext("Ready")} value={llmhost.ready} type="bool" />
        <DetailField label={gettext("RFC 1034 compliant name")} value={llmhost.rfc1034CompliantName} type="code" />
      </ResourceMetadataSection>
    </>
  );
}

export default DetailView;
