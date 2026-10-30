/**
 * CardView React Component
 *
 * This component renders proxy resources as individual cards, displaying detailed information and actions for each proxy.
 * It is used to present proxies in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays proxy details in a visually distinct card format.
 * - Integrates action buttons for copy URL, edit, clone, rename, and delete operations.
 * - Shows the Proxy's URL, which callers use as the base URL of the provider's SDK.
 * - Supports a custom detail row renderer for flexible display of proxy attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - proxies (Proxy[]): Array of proxy objects to display.
 * - renderDetailRow (function): Function to render detail rows for proxy attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your Proxies" objects={proxies} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { ProxyCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";
import { formatApiKey, formatAuth, proxyUrl } from "@/lib/format";

import "@/components/CardView/styles.css";
import { AnnotationsRow, gettext, interpolate, TagsRow } from "@smarter/common";

function CardView({ sessionContext, objects, onRequery, filtering }: ProxyCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((proxy) => (
          <div className="col-12" key={proxy.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} proxy={proxy} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar proxy={proxy} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={proxy.manifestUrl} className="text-decoration-none text-primary">
                    {proxy.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow(
                      gettext("URL"),
                      proxyUrl(proxy),
                      "string",
                      gettext("Use it as the base URL of the provider's SDK, with a Smarter API key."),
                    )}
                    {renderDetailRow(gettext("Provider"), proxy.providerName)}
                    {renderDetailRow(gettext("Provider API"), proxy.upstreamUrl, "string")}
                    {renderDetailRow(gettext("API Key Secret"), formatApiKey(proxy))}
                    {renderDetailRow(gettext("Auth Header"), formatAuth(proxy))}
                    {renderDetailRow(
                      gettext("Headers"),
                      Object.keys(proxy.headers || {}).length ? proxy.headers : null,
                      "json",
                    )}
                    {renderDetailRow(
                      gettext("Allowed Paths"),
                      proxy.allowedPaths?.length ? proxy.allowedPaths : gettext("All paths"),
                      "str[]",
                    )}
                    {renderDetailRow(
                      gettext("Timeout"),
                      interpolate(gettext("%(timeout)s seconds"), { timeout: proxy.timeout }),
                    )}
                    {renderDetailRow(gettext("Active"), proxy.isActive, "bool")}
                    {renderDetailRow(gettext("Manifest"), proxy.manifestUrl, "url")}
                    {renderDetailRow(gettext("Owner"), proxy.userProfile?.user?.username)}
                    {renderDetailRow(gettext("Account Number"), proxy.userProfile?.account?.accountNumber)}
                    {renderDetailRow(gettext("Created"), proxy.createdAt, "dateTime")}
                    {renderDetailRow(gettext("Last Updated"), proxy.updatedAt, "dateTime")}
                    {renderDetailRow(gettext("Version"), proxy.version)}
                    {renderDetailRow(gettext("Description"), proxy.description)}
                    <TagsRow tags={proxy.tags} filtering={filtering} />
                    <AnnotationsRow annotations={proxy.annotations} filtering={filtering} />
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
