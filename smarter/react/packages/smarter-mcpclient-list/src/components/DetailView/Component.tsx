/**
 * DetailView React Component
 *
 * The Details tab of an MCPClient's detail, which the list opens when one of its rows is chosen (see
 * TabbedListView and ResourceDetail in @smarter/common): the MCPClient's description, status and actions, then how
 * it connects to its MCP server, how it authenticates, what it offers the LLM, what the server reported at the last
 * connection, and the metadata that every resource has.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (MCPClient): The MCPClient.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={mcpclient} onRequery={onRequery} filtering={filtering} />
 */
import {
  DetailField,
  DetailOverview,
  DetailSection,
  DetailValue,
  gettext,
  ResourceMetadataSection,
} from "@smarter/common";

import type { MCPClientDetailViewProps, MCPConnectionStatus } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";

/** The badge class and label of each connection status. */
function connectionStatus(status: MCPConnectionStatus): { badge: string; label: string } {
  switch (status) {
    case "connected":
      return { badge: "badge-light-success", label: gettext("Connected") };
    case "disconnected":
      return { badge: "badge-light-warning", label: gettext("Disconnected") };
    case "error":
      return { badge: "badge-light-danger", label: gettext("Connection error") };
    default:
      return { badge: "badge-light", label: gettext("Not yet connected") };
  }
}

function DetailView({ sessionContext, object: mcpclient, onRequery, filtering }: MCPClientDetailViewProps) {
  const status = connectionStatus(mcpclient.status);
  const usesCredentials = mcpclient.authType !== "none";
  return (
    <>
      <DetailOverview description={mcpclient.description}>
        <span className={`badge ${mcpclient.isActive ? "badge-light-success" : "badge-light"} fw-semibold`}>
          {mcpclient.isActive ? gettext("Active") : gettext("Inactive")}
        </span>
        <span className={`badge ${status.badge} fw-semibold`}>{status.label}</span>
        <Toolbar sessionContext={sessionContext} mcpclient={mcpclient} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Connection")} icon="satellite">
        <DetailField label={gettext("Transport")} value={mcpclient.transport} type="code" />
        <DetailField
          label={gettext("Timeout (seconds)")}
          value={mcpclient.timeout}
          type="number"
          help={gettext("Seconds to wait for the MCP server to connect and respond.")}
        />
        <DetailField
          label={gettext("Endpoint URL")}
          value={mcpclient.endpointUrl}
          type="url"
          wide
          help={gettext("The https URL of the MCP server's endpoint.")}
        />
        {mcpclient.command && <DetailField label={gettext("Command")} value={mcpclient.command} type="source" wide />}
        <DetailField
          label={gettext("Headers")}
          wide
          help={gettext("Non-secret HTTP headers that are sent to the MCP server.")}
        >
          {mcpclient.headers && Object.keys(mcpclient.headers).length ? (
            <DetailValue value={mcpclient.headers} type="json" />
          ) : (
            <DetailValue value={null} />
          )}
        </DetailField>
      </DetailSection>

      <DetailSection title={gettext("Authentication")} icon="lock-2">
        <DetailField label={gettext("Authentication type")} value={mcpclient.authType} type="code" />
        {usesCredentials && (
          <DetailField
            label={gettext("Credentials")}
            value={mcpclient.credentials}
            type="code"
            help={gettext("The name of the Secret that holds the credential. Its value is never shown.")}
          />
        )}
        {mcpclient.authType === "api_key" && (
          <DetailField
            label={gettext("API key header")}
            value={mcpclient.apiKeyHeader}
            type="code"
            help={gettext("The HTTP header that carries the api key.")}
          />
        )}
      </DetailSection>

      <DetailSection title={gettext("Capabilities")} icon="setting-2">
        <DetailField
          label={gettext("Priority")}
          value={mcpclient.priority}
          type="number"
          help={gettext("The order in which an LLMClient's MCPClients are offered to the LLM; lower runs first.")}
        />
        <DetailField
          label={gettext("Cache TTL (seconds)")}
          value={mcpclient.cacheTtl}
          type="number"
          help={gettext("Seconds to cache the MCP server's tools, instructions and capabilities. 0 disables caching.")}
        />
        <DetailField
          label={gettext("Includes instructions")}
          value={mcpclient.includeInstructions}
          type="bool"
          help={gettext("Whether the MCP server's instructions are added to the system prompt.")}
        />
        <DetailField
          label={gettext("Allowed tools")}
          wide
          help={gettext(
            "Glob patterns of the tool names to offer the LLM. When empty, every tool that the server advertises is offered.",
          )}
        >
          {mcpclient.allowedTools?.length ? (
            <DetailValue value={mcpclient.allowedTools} type="list" />
          ) : (
            <span className="text-gray-600">{gettext("All tools")}</span>
          )}
        </DetailField>
        <DetailField
          label={gettext("Allowed resources")}
          wide
          help={gettext("Glob patterns of the resource URIs that the LLM may read. When empty, none.")}
        >
          {mcpclient.allowedResources?.length ? (
            <DetailValue value={mcpclient.allowedResources} type="list" />
          ) : (
            <span className="text-gray-600">{gettext("None")}</span>
          )}
        </DetailField>
      </DetailSection>

      <DetailSection title={gettext("MCP server")} icon="data">
        <DetailField
          label={gettext("Server name")}
          value={mcpclient.serverName}
          help={gettext("The name that the MCP server reported.")}
        />
        <DetailField
          label={gettext("Server version")}
          value={mcpclient.serverVersion}
          type="code"
          help={gettext("The version that the MCP server reported.")}
        />
        <DetailField
          label={gettext("Protocol version")}
          value={mcpclient.protocolVersion}
          type="code"
          help={gettext("The MCP protocol version negotiated at the last successful handshake.")}
        />
        <DetailField
          label={gettext("Last connected")}
          value={mcpclient.lastConnectedAt}
          type="dateTime"
          help={gettext("When Smarter last connected to the MCP server.")}
        />
        <DetailField
          label={gettext("Tools")}
          value={mcpclient.tools}
          type="list"
          wide
          help={gettext("The names of the tools offered to the LLM, as of the last successful connection.")}
        />
        {mcpclient.lastError && (
          <DetailField
            label={gettext("Last error")}
            value={mcpclient.lastError}
            type="code"
            wide
            help={gettext("The error of the last failed connection.")}
          />
        )}
      </DetailSection>

      <ResourceMetadataSection resource={mcpclient} filtering={filtering}>
        <DetailField
          label={gettext("Ready")}
          value={mcpclient.ready}
          type="bool"
          help={gettext("Whether the MCPClient is ready to serve requests.")}
        />
        <DetailField label={gettext("RFC 1034 compliant name")} value={mcpclient.rfc1034CompliantName} type="code" />
      </ResourceMetadataSection>
    </>
  );
}

export default DetailView;
