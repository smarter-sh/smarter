/**
 * DetailView React Component
 *
 * The Details tab of a vectorsearch's detail, which the list opens when one of its rows is chosen (see
 * TabbedListView and ResourceDetail in @smarter/common): the vectorsearch's description, status and actions, then
 * which vectorstore it queries, how it retrieves and ranks results, and the metadata that every resource has.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (Vectorsearch): The vectorsearch.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={vectorsearch} onRequery={onRequery} filtering={filtering} />
 */
import {
  DetailField,
  DetailOverview,
  DetailSection,
  DetailValue,
  gettext,
  ResourceMetadataSection,
} from "@smarter/common";

import type { VectorsearchDetailViewProps, VectorsearchSearchType } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";

/** The label of each search type. */
function searchTypeLabel(searchType: VectorsearchSearchType): string {
  switch (searchType) {
    case "similarity":
      return gettext("Similarity");
    case "similarity_score_threshold":
      return gettext("Similarity, above a score threshold");
    case "mmr":
      return gettext("Maximal marginal relevance (MMR)");
    default:
      return searchType;
  }
}

function DetailView({ sessionContext, object: vectorsearch, onRequery, filtering }: VectorsearchDetailViewProps) {
  const usesThreshold = vectorsearch.searchType === "similarity_score_threshold" || vectorsearch.scoreThreshold != null;
  const usesMmr = vectorsearch.searchType === "mmr" || vectorsearch.fetchK != null || vectorsearch.lambdaMult != null;
  return (
    <>
      <DetailOverview description={vectorsearch.description}>
        <span
          className={`badge ${vectorsearch.isEnabled ? "badge-light-success" : "badge-light"} fw-semibold`}
          title={gettext("Whether this vectorsearch is active and may be queried.")}
        >
          {vectorsearch.isEnabled ? gettext("Enabled") : gettext("Disabled")}
        </span>
        <Toolbar sessionContext={sessionContext} vectorsearch={vectorsearch} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Source")} icon="data">
        <DetailField
          label={gettext("Vectorstore")}
          value={vectorsearch.vectorstore}
          type="code"
          help={gettext("The vectorstore that this search queries.")}
        />
        <DetailField
          label={gettext("Authentication secret")}
          value={vectorsearch.authSecret}
          type="code"
          help={gettext(
            "The Secret that holds the credential for the vectorstore, if it needs one. Its value is never shown.",
          )}
        />
      </DetailSection>

      <DetailSection title={gettext("Retrieval")} icon="magnifier">
        <DetailField
          label={gettext("Search type")}
          help={gettext("The retrieval strategy to use when querying the vectorstore.")}
        >
          <span>{searchTypeLabel(vectorsearch.searchType)}</span>
          <code className="smarter-detail-code ms-2">{vectorsearch.searchType}</code>
        </DetailField>
        <DetailField
          label={gettext("Results (k)")}
          value={vectorsearch.k}
          type="number"
          help={gettext("The number of top results to return from the search.")}
        />
        {usesThreshold && (
          <DetailField
            label={gettext("Score threshold")}
            value={vectorsearch.scoreThreshold}
            type="number"
            help={gettext(
              "The minimum relevance score, from 0.0 to 1.0, that a result must have to be included. Used by the similarity score threshold search type.",
            )}
          />
        )}
        {usesMmr && (
          <DetailField
            label={gettext("Candidates (fetch k)")}
            value={vectorsearch.fetchK}
            type="number"
            help={gettext("The number of candidate documents to fetch before MMR re-ranks them.")}
          />
        )}
        {usesMmr && (
          <DetailField
            label={gettext("Diversity (lambda)")}
            value={vectorsearch.lambdaMult}
            type="number"
            help={gettext(
              "MMR's trade-off between diversity and relevance, from 0.0 (most diverse) to 1.0 (most relevant).",
            )}
          />
        )}
        <DetailField
          label={gettext("Metadata filter")}
          wide
          help={gettext("A filter on the documents' metadata that is applied to every query, e.g. {'source': 'faq'}.")}
        >
          {vectorsearch.metadataFilter && Object.keys(vectorsearch.metadataFilter).length ? (
            <DetailValue value={vectorsearch.metadataFilter} type="json" />
          ) : (
            <DetailValue value={null} />
          )}
        </DetailField>
      </DetailSection>

      <ResourceMetadataSection resource={vectorsearch} filtering={filtering}>
        <DetailField
          label={gettext("Ready")}
          value={vectorsearch.ready}
          type="bool"
          help={gettext("Whether the vectorsearch is ready to serve requests.")}
        />
        <DetailField label={gettext("RFC 1034 compliant name")} value={vectorsearch.rfc1034CompliantName} type="code" />
      </ResourceMetadataSection>
    </>
  );
}

export default DetailView;
