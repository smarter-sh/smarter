/**
 * DetailView React Component
 *
 * The Details tab of an authtoken's detail, which the list opens when one of its rows is chosen (see
 * TabbedListView and ResourceDetail in @smarter/common): the authtoken's description, status and actions, then
 * whether and when it is used, and the metadata that every resource has. The key itself is never shown: Smarter
 * keeps only its hash.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (AuthToken): The authtoken.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={authtoken} onRequery={onRequery} filtering={filtering} />
 */
import { DetailField, DetailOverview, DetailSection, gettext, ResourceMetadataSection } from "@smarter/common";

import type { AuthTokenDetailViewProps } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";

function DetailView({ sessionContext, object: authtoken, onRequery, filtering }: AuthTokenDetailViewProps) {
  return (
    <>
      <DetailOverview description={authtoken.description}>
        <span className={`badge ${authtoken.isActive ? "badge-light-success" : "badge-light"} fw-semibold`}>
          {authtoken.isActive ? gettext("Active") : gettext("Inactive")}
        </span>
        <Toolbar sessionContext={sessionContext} authtoken={authtoken} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Status")} icon="key">
        <DetailField
          label={gettext("Active")}
          value={authtoken.isActive}
          type="bool"
          help={gettext("Whether the key may be used. A request with an inactive key is refused.")}
        />
        <DetailField label={gettext("Ready")} value={authtoken.ready} type="bool" />
        <DetailField
          label={gettext("Last used")}
          value={authtoken.lastUsedAt}
          type="dateTime"
          help={gettext("When the key last authenticated a request. Empty if it never has.")}
        />
        <DetailField
          label={gettext("Key")}
          value={gettext("Shown only once, when the key is created.")}
          help={gettext(
            "Smarter keeps only a hash of the key, so it can't be shown again. Its ID is its public identifier.",
          )}
        />
      </DetailSection>

      <ResourceMetadataSection resource={authtoken} filtering={filtering} />
    </>
  );
}

export default DetailView;
