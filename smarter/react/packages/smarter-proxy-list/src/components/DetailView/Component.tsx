/**
 * DetailView React Component
 *
 * The Details tab of a Proxy's detail, which the list opens when one of its rows is chosen (see TabbedListView
 * and ResourceDetail in @smarter/common): the Proxy's description, status and actions, then the URL that callers
 * use, where and how it forwards their requests, how it authenticates with the provider, and the metadata that
 * every resource has. The provider's API key is never shown: only the name of the Secret that holds it.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (Proxy): The Proxy.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={proxy} onRequery={onRequery} filtering={filtering} />
 */
import {
  DetailField,
  DetailOverview,
  DetailSection,
  DetailValue,
  gettext,
  interpolate,
  ResourceMetadataSection,
} from "@smarter/common";

import type { ProxyDetailViewProps } from "@/lib/Types";
import { StatusBar } from "@/components/StatusBar";
import { Toolbar } from "@/components/Toolbar";
import { formatApiKey, formatAuth, proxyUrl } from "@/lib/format";

function DetailView({ sessionContext, object: proxy, onRequery, filtering }: ProxyDetailViewProps) {
  const headers = proxy.headers && Object.keys(proxy.headers).length ? proxy.headers : null;
  return (
    <>
      <DetailOverview description={proxy.description}>
        <span className={`badge ${proxy.isActive ? "badge-light-success" : "badge-light"} fw-semibold`}>
          {proxy.isActive ? gettext("Active") : gettext("Inactive")}
        </span>
        <StatusBar proxy={proxy} />
        <Toolbar sessionContext={sessionContext} proxy={proxy} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Endpoint")} icon="route">
        <DetailField
          label={gettext("URL")}
          value={proxyUrl(proxy)}
          type="code"
          wide
          help={gettext("Use it as the base URL of the provider's SDK, with a Smarter API key.")}
        />
      </DetailSection>

      <DetailSection title={gettext("Forwarding")} icon="send">
        <DetailField label={gettext("Provider")} value={proxy.providerName} />
        <DetailField
          label={gettext("Timeout")}
          value={interpolate(gettext("%(timeout)s seconds"), { timeout: proxy.timeout })}
          help={gettext("How long the Proxy waits for the provider's reply.")}
        />
        <DetailField
          label={gettext("Provider API")}
          value={proxy.upstreamUrl}
          type="code"
          wide
          help={gettext("The base URL to which requests are forwarded: the Proxy's own, else its Provider's.")}
        />
        <DetailField
          label={gettext("Allowed paths")}
          wide
          help={gettext("Glob patterns of the paths of the provider's API that callers may use.")}
        >
          {proxy.allowedPaths?.length ? (
            <DetailValue value={proxy.allowedPaths} type="list" />
          ) : (
            <span className="badge badge-light-warning fw-semibold">{gettext("All paths")}</span>
          )}
        </DetailField>
        <DetailField
          label={gettext("Headers")}
          wide
          help={gettext("Headers that the Proxy adds to every request, e.g. the version of the provider's API.")}
        >
          <DetailValue value={headers} type="json" />
        </DetailField>
      </DetailSection>

      <DetailSection title={gettext("Authentication")} icon="key">
        <DetailField
          label={gettext("API key Secret")}
          value={formatApiKey(proxy)}
          help={gettext(
            "The Secret whose API key the Proxy adds to every request: the Proxy's own, else its Provider's. The key itself is never shown.",
          )}
        />
        <DetailField
          label={gettext("Auth header")}
          value={formatAuth(proxy)}
          type="code"
          help={gettext("The header, and its prefix, in which the provider expects its API key.")}
        />
      </DetailSection>

      <ResourceMetadataSection resource={proxy} filtering={filtering} />
    </>
  );
}

export default DetailView;
