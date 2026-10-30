/**
 * DetailView React Component
 *
 * The Details tab of a custom domain's detail, which the list opens when one of its rows is chosen (see
 * TabbedListView and ResourceDetail in @smarter/common): the domain's description, verification status and
 * actions, then the domain and its verification, the LLMClient that it serves, the DNS records that delegate it
 * to Smarter, and the metadata that every resource has.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (CustomDomain): The custom domain.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={customDomain} onRequery={onRequery} filtering={filtering} />
 */
import {
  DetailField,
  DetailOverview,
  DetailSection,
  DetailValue,
  gettext,
  ResourceMetadataSection,
} from "@smarter/common";

import type { CustomDomainDnsRecord, CustomDomainDetailViewProps } from "@/lib/Types";
import { StatusBar } from "@/components/StatusBar";
import { VerificationBadge } from "@/components/StatusBar/VerificationBadge";
import { Toolbar } from "@/components/Toolbar";

/** The domain's DNS records, as a zone file shows them: name, TTL, type and value. */
function DnsRecords({ records }: { records: CustomDomainDnsRecord[] | null | undefined }) {
  if (!records || records.length === 0) return <DetailValue value={null} />;
  return (
    <div className="table-responsive">
      <table className="table table-sm table-row-dashed align-middle mb-0">
        <thead>
          <tr className="text-gray-600 fw-semibold">
            <th scope="col">{gettext("Name")}</th>
            <th scope="col">{gettext("TTL")}</th>
            <th scope="col">{gettext("Type")}</th>
            <th scope="col">{gettext("Value")}</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record, index) => (
            <tr key={`${record.name}-${record.type}-${index}`}>
              <td>
                <code className="smarter-detail-code">{record.name}</code>
              </td>
              <td>
                <DetailValue value={record.ttl} type="number" />
              </td>
              <td>
                <span className="badge badge-light text-gray-800 fw-semibold">{record.type}</span>
              </td>
              <td>
                <code className="smarter-detail-code text-break">{record.value}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DetailView({ sessionContext, object: customDomain, onRequery, filtering }: CustomDomainDetailViewProps) {
  const llmclient = customDomain.llmclient;
  return (
    <>
      <DetailOverview description={customDomain.description}>
        <VerificationBadge customDomain={customDomain} />
        <StatusBar customDomain={customDomain} />
        <Toolbar sessionContext={sessionContext} customDomain={customDomain} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Domain")} icon="globe">
        <DetailField label={gettext("Domain")} value={customDomain.domainName} type="code" />
        <DetailField
          label={gettext("Verification status")}
          help={gettext(
            "A custom domain is verified when its DNS is delegated to Smarter, and its TLS certificate is issued.",
          )}
        >
          <VerificationBadge customDomain={customDomain} />
        </DetailField>
        <DetailField label={gettext("Verified")} value={customDomain.verifiedAt} type="dateTime" />
        <DetailField
          label={gettext("AWS hosted zone ID")}
          value={customDomain.awsHostedZoneId}
          type="code"
          help={gettext("The DNS hosted zone that holds the domain's records.")}
        />
        <DetailField
          label={gettext("Verification message")}
          value={customDomain.verificationMessage}
          wide
          help={gettext("Why the domain is not verified yet, or why its verification failed.")}
        />
      </DetailSection>

      <DetailSection title={gettext("LLMClient")} icon="artificial-intelligence">
        {llmclient ? (
          <>
            <DetailField label={gettext("Name")}>
              <a href={llmclient.manifestUrl} className="smarter-detail-link">
                {llmclient.name}
              </a>
            </DetailField>
            <DetailField label={gettext("Owner")} value={llmclient.owner} />
            <DetailField label={gettext("Deployed")} value={llmclient.deployed} type="bool" />
            <DetailField
              label={gettext("URL")}
              value={llmclient.url}
              type="url"
              wide
              help={gettext("The LLMClient's url on this custom domain.")}
            />
          </>
        ) : (
          <DetailField label={gettext("Name")} wide>
            <span className="text-gray-600 fst-italic">{gettext("No LLMClient uses this domain")}</span>
          </DetailField>
        )}
      </DetailSection>

      <DetailSection title={gettext("DNS records")} icon="router">
        <DetailField
          label={gettext("Records")}
          wide
          help={gettext(
            "The records of the domain's hosted zone. Its NS records are the name servers that the domain's registrar must delegate it to.",
          )}
        >
          <DnsRecords records={customDomain.dnsRecords} />
        </DetailField>
      </DetailSection>

      <ResourceMetadataSection resource={customDomain} filtering={filtering} />
    </>
  );
}

export default DetailView;
