/**
 * GlobalSearch dashboard widget.
 *
 * A search box that finds the resources of every kind that the user may read, and shows them
 * grouped by list: Guardrails, Secrets, LLMClients, and so on. A query is one of:
 *
 * - text, e.g. "support": resources whose name or description contains it, or that have that tag;
 * - "tag:<name>", e.g. "tag:production": resources with that tag;
 * - an annotation selector requirement, e.g. "acme.com/crm-id=A-10042" or "!acme.com/archived".
 *
 * The search is requested once typing pauses. Each group shows a few results, each linking to its
 * resource, and links to its list, narrowed by the same query, for the rest. The backend
 * (smarter.apps.dashboard.search) searches with each list's own permissions.
 *
 * :param sessionContext: Session context used for authenticated requests.
 * :param apiUrl: The global search api, e.g. /dashboard/api/search/.
 *
 * :example:
 *
 *     <GlobalSearch sessionContext={sessionContext} apiUrl="/dashboard/api/search/" />
 */
import { useEffect, useId, useRef, useState } from "react";
import type { SessionContext } from "@smarter/common";
import { fetchDjangoUrl, gettext, interpolate, Loading, ngettext } from "@smarter/common";

import { loggerPrefix } from "@/const";

/** How long to wait after the last keystroke before searching, in milliseconds. */
export const GLOBAL_SEARCH_DELAY_MS = 300;

export interface GlobalSearchResult {
  name: string;
  description: string;
  url: string;
}

export interface GlobalSearchGroup {
  label: string;
  count: number;
  url: string;
  results: GlobalSearchResult[];
}

/** The response of the global search api, a GlobalSearchResponse of smarter.apps.dashboard.search. */
export interface GlobalSearchResponse {
  query: string;
  mode: "text" | "tag" | "annotation";
  error: string;
  count: number;
  groups: GlobalSearchGroup[];
}

interface GlobalSearchProps {
  sessionContext: SessionContext;
  apiUrl: string;
}

type SearchState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; response: GlobalSearchResponse }
  | { status: "failed"; error: string };

function GlobalSearch({ sessionContext, apiUrl }: GlobalSearchProps) {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<SearchState>({ status: "idle" });
  // only the latest search's response is shown, when several are in flight.
  const latest = useRef(0);
  const hintId = useId();

  useEffect(() => {
    const requested = query.trim();
    const request = latest.current + 1;
    latest.current = request;
    // an empty box shows nothing (see shown, below), and requests nothing.
    if (!requested) return;
    const timer = window.setTimeout(() => {
      setState({ status: "loading" });
      fetchDjangoUrl(sessionContext, apiUrl, JSON.stringify({ query: requested }))
        .then(async (response) => {
          if (!response.ok)
            throw new Error(interpolate(gettext("Request failed: %(status)s"), { status: response.status }));
          return (await response.json()) as GlobalSearchResponse;
        })
        .then((response) => {
          if (request === latest.current) setState({ status: "done", response });
        })
        .catch((error: Error) => {
          console.error(loggerPrefix, "GlobalSearch failed", error);
          if (request === latest.current) setState({ status: "failed", error: error.message });
        });
    }, GLOBAL_SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [query, sessionContext, apiUrl]);
  const shown: SearchState = query.trim() ? state : { status: "idle" };

  return (
    <section id="global-search" aria-label={gettext("Search")} className="col-xl-12 mb-5 mb-xl-10">
      <div className="card card-flush">
        <div className="card-body py-5">
          <div className="position-relative">
            <i
              className="ki-outline ki-magnifier fs-2 position-absolute top-50 translate-middle-y ms-4 text-muted"
              aria-hidden="true"
            />
            <input
              type="search"
              className="form-control form-control-solid ps-13"
              placeholder={gettext("Search every resource by name, description, tag or annotation")}
              aria-label={gettext("Search every resource")}
              aria-describedby={hintId}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <div id={hintId} className="text-muted fs-8 mt-2">
            {gettext(
              "Type text, tag:production, or an annotation such as acme.com/crm-id=A-10042 or !acme.com/archived.",
            )}
          </div>
          <SearchResults state={shown} />
        </div>
      </div>
    </section>
  );
}

function SearchResults({ state }: { state: SearchState }) {
  if (state.status === "idle") return null;
  if (state.status === "loading") return <Loading />;
  if (state.status === "failed") {
    return (
      <div className="text-danger fs-7 mt-4" role="alert">
        {interpolate(gettext("Search failed: %(error)s"), { error: state.error })}
      </div>
    );
  }
  const { response } = state;
  if (response.error) {
    return (
      <div className="text-danger fs-7 mt-4" role="alert">
        {response.error}
      </div>
    );
  }
  if (!response.groups.length) {
    return (
      <div className="text-muted fs-7 mt-4" role="status">
        {interpolate(gettext("Nothing matches %(query)s."), { query: response.query })}
      </div>
    );
  }
  return (
    <div className="mt-4">
      <div className="text-gray-700 fs-7 mb-3" role="status">
        {interpolate(ngettext("%(count)s resource matches.", "%(count)s resources match.", response.count), {
          count: response.count,
        })}
      </div>
      <div className="row g-4">
        {response.groups.map((group) => (
          <div key={group.label} className="col-md-6 col-xl-4">
            <div className="border rounded p-3 h-100">
              <h5 className="fs-6 fw-bold mb-2">
                {group.label} <span className="badge badge-light-primary ms-1">{group.count}</span>
              </h5>
              <ul className="list-unstyled mb-2" aria-label={group.label}>
                {group.results.map((result) => (
                  <li key={result.url} className="mb-1 text-truncate">
                    <a href={result.url} title={result.description || result.name} className="fw-semibold">
                      {result.name}
                    </a>
                  </li>
                ))}
              </ul>
              {group.count > group.results.length && (
                <a href={group.url} className="fs-7">
                  {
                    // Translators: list is a list's name, e.g. Guardrails.
                    interpolate(gettext("See all %(count)s in %(list)s"), { count: group.count, list: group.label })
                  }
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default GlobalSearch;
