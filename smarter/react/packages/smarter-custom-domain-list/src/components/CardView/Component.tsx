/**
 * CardView React Component
 *
 * This component renders custom domains as individual cards, displaying detailed information
 * and links for each domain, including the DNS records of its AWS Route53 hosted zone.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - objects (CustomDomain[]): Array of custom domain objects to display.
 * - onRequery (function): Callback to refresh custom domain data.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} objects={customDomains} onRequery={onRequery} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { CustomDomainCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar, VerificationBadge } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "@/components/CardView/styles.css";
import { gettext } from "@smarter/common";

function CardView({ sessionContext, objects, onRequery }: CustomDomainCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((customDomain) => (
          <div className="col-12" key={customDomain.id}>
            <div className="card h-100 custom-domain-card">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} customDomain={customDomain} onRequery={onRequery} />
                <span className="border rounded p-2 d-flex align-items-center gap-2">
                  <VerificationBadge customDomain={customDomain} />
                  <StatusBar customDomain={customDomain} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={customDomain.manifestUrl} className="text-decoration-none text-primary">
                    {customDomain.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow(gettext("ID"), customDomain.id, "number")}
                    {renderDetailRow(gettext("Manifest URL"), customDomain.manifestUrl, "url")}
                    {renderDetailRow(gettext("Owner"), customDomain.userProfile?.user?.username)}
                    {renderDetailRow(gettext("Account Number"), customDomain.userProfile?.account?.accountNumber)}
                    {renderDetailRow(gettext("Domain"), customDomain.domainName)}
                    {renderDetailRow(gettext("Verification Status"), customDomain.verificationStatus)}
                    {renderDetailRow(gettext("Verified"), customDomain.verifiedAt, "dateTime")}
                    {renderDetailRow(gettext("Verification Message"), customDomain.verificationMessage)}
                    {renderDetailRow(gettext("AWS Hosted Zone ID"), customDomain.awsHostedZoneId)}
                    {renderDetailRow(gettext("LLMClient"), customDomain.llmclient?.name)}
                    {renderDetailRow(gettext("LLMClient Owner"), customDomain.llmclient?.owner)}
                    {renderDetailRow(gettext("LLMClient Deployed"), customDomain.llmclient?.deployed, "bool")}
                    {renderDetailRow(gettext("LLMClient URL"), customDomain.llmclient?.url, "url")}
                    {renderDetailRow(gettext("Created"), customDomain.createdAt, "dateTime")}
                    {renderDetailRow(gettext("Last Updated"), customDomain.updatedAt, "dateTime")}
                    {renderDetailRow(gettext("Version"), customDomain.version)}
                    {renderDetailRow(gettext("Description"), customDomain.description)}
                    {renderDetailRow(gettext("Tags"), customDomain.tags, "str[]")}
                    {renderDetailRow(gettext("Annotations"), customDomain.annotations, "json")}
                    {renderDetailRow(
                      gettext("DNS Records"),
                      customDomain.dnsRecords?.map(
                        (record) => `${record.name} ${record.ttl ?? ""} ${record.type} ${record.value}`,
                      ),
                      "str[]",
                    )}
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
