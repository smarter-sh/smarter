/**
 * DetailView React Component
 *
 * The Details tab of an llmclient's detail, which the list opens when one of its rows is chosen (see
 * TabbedListView and ResourceDetail in @smarter/common): the llmclient's description, status and actions, then
 * its model, its tools, its chat app, who may call it, its endpoints, where it is hosted, and the metadata that
 * every resource has.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (LLMClient): The llmclient.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={llmclient} onRequery={onRequery} filtering={filtering} />
 */
import {
  DetailField,
  DetailOverview,
  DetailSection,
  DetailValue,
  gettext,
  ResourceMetadataSection,
} from "@smarter/common";

import type { LLMClientCustomDomain, LLMClientDetailViewProps } from "@/lib/Types";
import { StatusBar } from "@/components/StatusBar";
import { Toolbar } from "@/components/Toolbar";

/** The names of an llmclient's plugins, MCPClients or guardrails. */
const names = (items?: Array<{ name: string }>) =>
  Array.isArray(items) ? items.map((item) => item?.name).filter(Boolean) : [];

/** A custom domain, with its verification status, e.g. "chat.example.com (verified)". */
const customDomainLabel = (domain: LLMClientCustomDomain) =>
  domain.verificationStatus ? `${domain.domainName} (${domain.verificationStatus})` : domain.domainName;

function DetailView({ sessionContext, object: llmclient, onRequery, filtering }: LLMClientDetailViewProps) {
  const functions = Array.isArray(llmclient.functions)
    ? llmclient.functions.map((f) => (f?.name ? `${f.name}()` : "")).filter(Boolean)
    : [];
  const customDomains = Array.isArray(llmclient.customDomains)
    ? llmclient.customDomains.map(customDomainLabel).filter(Boolean)
    : [];
  // an api key's public key_id: the key itself is never sent.
  const apiKeys = Array.isArray(llmclient.apiKeys) ? llmclient.apiKeys.map((key) => key?.apiKey).filter(Boolean) : [];

  return (
    <>
      <DetailOverview description={llmclient.description}>
        <span className={`badge ${llmclient.deployed ? "badge-light-success" : "badge-light-warning"} fw-semibold`}>
          {llmclient.deployed ? gettext("Deployed") : gettext("Not deployed")}
        </span>
        <span className={`badge ${llmclient.ready ? "badge-light-primary" : "badge-light"} fw-semibold`}>
          {llmclient.ready ? gettext("Ready") : gettext("Not ready")}
        </span>
        <StatusBar llmclient={llmclient} />
        <Toolbar sessionContext={sessionContext} llmclient={llmclient} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Model")} icon="artificial-intelligence">
        <DetailField label={gettext("Provider")} value={llmclient.provider} />
        <DetailField
          label={gettext("Model")}
          value={llmclient.defaultModel}
          type="code"
          help={gettext("When empty, the provider's default model is used.")}
        />
        <DetailField
          label={gettext("Temperature")}
          value={llmclient.defaultTemperature}
          type="number"
          help={gettext("Higher values make the LLM's replies more varied, lower values more predictable.")}
        />
        <DetailField
          label={gettext("Max tokens")}
          value={llmclient.defaultMaxTokens}
          type="number"
          help={gettext("The most tokens that the LLM may generate in one reply.")}
        />
        <DetailField
          label={gettext("System role")}
          value={llmclient.defaultSystemRole}
          wide
          help={gettext("The instructions that the LLM is given at the start of every conversation.")}
        />
      </DetailSection>

      <DetailSection title={gettext("Tools")} icon="wrench">
        <DetailField
          label={gettext("Functions")}
          value={functions}
          type="list"
          wide
          help={gettext("The functions attached to this llmclient, which the LLM may call.")}
        />
        <DetailField
          label={gettext("Plugins")}
          value={names(llmclient.plugins)}
          type="list"
          wide
          help={gettext("The plugins attached to this llmclient.")}
        />
        <DetailField
          label={gettext("MCP Clients")}
          value={names(llmclient.mcpclients)}
          type="list"
          wide
          help={gettext("The MCPClients whose MCP servers' tools this llmclient offers the LLM.")}
        />
        <DetailField
          label={gettext("Guardrails")}
          value={names(llmclient.guardrails)}
          type="list"
          wide
          help={gettext("The guardrails that check this llmclient's prompts and replies.")}
        />
      </DetailSection>

      <DetailSection title={gettext("Chat app")} icon="message-text-2">
        <DetailField label={gettext("App name")} value={llmclient.appName} />
        <DetailField label={gettext("Assistant")} value={llmclient.appAssistant} />
        <DetailField label={gettext("Placeholder")} value={llmclient.appPlaceholder} />
        <DetailField label={gettext("File attachments")} value={llmclient.appFileAttachment} type="bool" />
        <DetailField label={gettext("Welcome message")} value={llmclient.appWelcomeMessage} wide />
        <DetailField label={gettext("Example prompts")} value={llmclient.appExamplePrompts} type="list" wide />
        <DetailField label={gettext("Info URL")} value={llmclient.appInfoUrl} type="url" />
        <DetailField label={gettext("Logo URL")} value={llmclient.styles?.appLogoUrl ?? null} type="url" />
        <DetailField
          label={gettext("Background image URL")}
          value={llmclient.styles?.appBackgroundImageUrl ?? null}
          type="url"
        />
        <DetailField
          label={gettext("Styles")}
          wide
          help={gettext("The look of the llmclient's chat: its manifest's spec.config.styles.")}
        >
          {llmclient.styles && Object.keys(llmclient.styles).length ? (
            <DetailValue value={llmclient.styles} type="css" />
          ) : (
            <DetailValue value={null} />
          )}
        </DetailField>
      </DetailSection>

      <DetailSection title={gettext("Authentication")} icon="shield-tick">
        <DetailField
          label={gettext("Authentication required")}
          value={llmclient.isAuthenticationRequired}
          type="bool"
          help={gettext("Whether one or more active API keys are attached to this llmclient.")}
        />
        <DetailField
          label={gettext("API keys")}
          value={apiKeys}
          type="list"
          wide
          help={gettext("The ids of the API keys that may call this llmclient. The keys themselves are never shown.")}
        />
      </DetailSection>

      <DetailSection title={gettext("Cross-origin access (CORS)")} icon="global">
        <p className="smarter-detail-field-wide text-gray-600 mb-0">
          {gettext(
            "A browser lets a web page call the llmclient's api only from the llmclient's own hosts, and from these origins. Add the origin of each website that embeds its chat.",
          )}
        </p>
        <DetailField
          label={gettext("Allowed origins")}
          value={llmclient.allowedOrigins}
          type="list"
          wide
          help={gettext("Its manifest's spec.config.prompt.allowedOrigins.")}
        />
      </DetailSection>

      <DetailSection title={gettext("Endpoints")} icon="route">
        <DetailField
          label={gettext("Chat")}
          value={llmclient.urlChatapp}
          type="url"
          wide
          help={gettext("The llmclient's chat, in the Prompt Engineer's Workbench.")}
        />
        <DetailField
          label={gettext("LLMClient API")}
          value={llmclient.urlLlmclient}
          type="url"
          wide
          help={gettext("POST only endpoint for llmclient interactions.")}
        />
        <DetailField
          label={gettext("Chat config API")}
          value={llmclient.urlChatConfig}
          type="url"
          wide
          help={gettext("POST only endpoint for llmclient configuration retrieval.")}
        />
        <DetailField
          label={gettext("Base URL")}
          value={llmclient.url}
          type="url"
          wide
          help={gettext(
            "Note that the base URL does not resolve to a working endpoint. Add '/chat' or '/config' to this URL.",
          )}
        />
        <DetailField label={gettext("Default URL")} value={llmclient.defaultUrl} type="url" wide />
        <DetailField label={gettext("Sandbox URL")} value={llmclient.sandboxUrl} type="url" wide />
        <DetailField
          label={gettext("Custom URL")}
          value={llmclient.customUrl}
          type="url"
          wide
          help={gettext("Custom domain and base URL set by the user, if any.")}
        />
      </DetailSection>

      <DetailSection title={gettext("Hosting")} icon="global">
        <DetailField label={gettext("Hostname")} value={llmclient.hostname} type="code" />
        <DetailField label={gettext("Default host")} value={llmclient.defaultHost} type="code" />
        <DetailField label={gettext("Base default host")} value={llmclient.baseDefaultHost} type="code" />
        <DetailField label={gettext("Base API domain")} value={llmclient.baseApiDomain} type="code" />
        <DetailField label={gettext("Sandbox host")} value={llmclient.sandboxHost} type="code" />
        <DetailField
          label={gettext("Custom host")}
          value={llmclient.customHost}
          type="code"
          help={gettext("Custom host set by the user, if any.")}
        />
        <DetailField label={gettext("Subdomain")} value={llmclient.subdomain} type="code" />
        <DetailField label={gettext("Custom domain")} value={llmclient.customDomain} type="code" />
        <DetailField label={gettext("DNS verification")} value={llmclient.dnsVerificationStatus} />
        <DetailField label={gettext("TLS certificate")} value={llmclient.tlsCertificateIssuanceStatus} />
        <DetailField label={gettext("Custom domains")} value={customDomains} type="list" wide />
      </DetailSection>

      <ResourceMetadataSection resource={llmclient} filtering={filtering}>
        <DetailField
          label={gettext("RFC 1034 compliant name")}
          value={llmclient.rfc1034CompliantName}
          type="code"
          help={gettext("RFC 1034 compliant name derived from the llmclient name, used for subdomain generation.")}
        />
      </ResourceMetadataSection>
    </>
  );
}

export default DetailView;
