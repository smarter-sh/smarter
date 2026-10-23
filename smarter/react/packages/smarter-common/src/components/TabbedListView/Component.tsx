/**
 * TabbedListView React Component
 *
 * Displays a tabbed interface for viewing objects owned by the current user
 * and objects shared with the user, one page at a time.
 *
 * Tabs:
 * - Your LLMClients
 * - Shared LLMClients
 *
 * The tabs are those of the tabbedListViewContext, whose keys are the slugs of the list api that
 * loads them, e.g. "owned" and "shared". A tab may also have its own ListView, CardView and object
 * type name, e.g. the read-only Extensions tab of the LLMTool list, whose objects are not LLMTools.
 *
 * View Modes:
 * - List
 * - Thumbnail card
 *
 * Features:
 * - Loads owned and shared llmclient lists from the backend using session context.
 * - Paginates each tab: previous and next page buttons, and a page number box. The backend
 *   paginates, so each page is a request to the list api, for ?page=N.
 * - Searches both tabs: the backend searches all of the objects, not only the page shown, so
 *   the search is a request to the list api, for ?search=..., once typing pauses. A new search
 *   returns each tab to its first page.
 * - Sorts both tabs by a column, when the list view's header of the column is clicked (see
 *   SortableHeader): the backend sorts all of the objects, not only the page shown, so a new sort
 *   is a request to the list api, for ?ordering=name or ?ordering=-name, and it returns each tab
 *   to its first page. The list api says which columns it can sort by.
 * - Narrows both tabs by a named filter of the list api, when the page is opened with
 *   ?filter=<name>, e.g. the dashboard's pending deployments link, ?filter=pending. A chip shows the
 *   filter's label, from the tabbedListViewContext's filters, and a button that removes it.
 * - Shows a page from the cache at once, when it holds it, while the page is fetched again, with a
 *   small spinner that says it is refreshing.
 * - Shows loading and error states during fetches.
 * - Allows switching between list and card views.
 * - Persists the selected view mode in sessionStorage.
 * - Uses cookie-backed counts (owned/shared) to size loading skeleton rows.
 * - Supports requery with cache invalidation.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context used for requests.
 *
 * State:
 * - lists: Each tab's objects, loading state, and pagination, as the list api last described it.
 * - pages: Each tab's requested page.
 * - searchInput: The search as typed; search: the search requested, once typing pauses.
 * - ordering: The column that sorts both tabs, e.g. "name", or "-name" in descending order. Empty for the default order.
 * - errorMessage: Error text for failed requests.
 * - viewMode: Current display mode ("list" or "thumbnail").
 * - activeTab: Current tab, the key of one of the tabbedListViewContext's tabs, e.g. "owned".
 *
 * Internal Helpers:
 * - getCookie: Reads cookie values used for skeleton sizing.
 * - load (from ./load): Fetches llmclient data and updates state via setters.
 *
 * Page Rendering Performance and Caching behavior:
 * - Improves the perceived load time by rendering cached results immediately when
 *   available while a fresh backend fetch is still in flight (stale-while-revalidate). The list
 *   api caches its pages too (smarter.lib.django.listview), so the fresh fetch is usually quick.
 * - Reads each page from localStorage, keyed by the session, the API URL, the tab, and the page's
 *   page number, ordering and filter, on mount and whenever the page, ordering or filter changes.
 * - Writes every successful fetch without a search back to the cache, with its pagination, so that
 *   a return visit, a new browser tab, or paging back shows recent data without waiting on the network.
 *
 * Usage:
 * <TabbedListView sessionContext={sessionContext} />
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type {
  CardViewBaseProps,
  ListViewBaseProps,
  Pagination,
  SessionContext,
  Sorting,
  TabbedViewContext,
  TabKey,
} from "../../lib/Types";
import { load } from "../../lib/load";
import { loggerPrefix } from "../../lib/const";
import { makeCacheKey, readCache, sessionScope, writeCache } from "../../lib/cache";

import ToggleButton from "../ToggleButton";
import type { ViewMode } from "../ToggleButton";

import { getCookieForUrl } from "./cookie";
import { PaginationControls } from "./PaginationControls";
import { SearchBox } from "./SearchBox";
import { TabNav } from "./TabNavigation";
import { gettext, interpolate } from "../../lib/i18n";

type TabbedListViewProps<TObject> = {
  sessionContext: SessionContext;
  tabbedListViewContext: TabbedViewContext<TObject>;
};

// a tab's objects are of the list's object type, or of the tab's own (see Tab), so the tabbed
// list view holds them as unknown, and its views say what they are.
type TabList = {
  objects: unknown[];
  isLoading: boolean;
  /** Whether the objects shown are cached ones, while the list api is asked for fresh ones. */
  isRefreshing: boolean;
  pagination: Pagination | null;
};

type TabRecord<T> = Record<TabKey, T>;

/** A record with a value for each tab. */
function tabRecord<T>(tabKeys: TabKey[], value: (tab: TabKey) => T): TabRecord<T> {
  return Object.fromEntries(tabKeys.map((tab) => [tab, value(tab)])) as TabRecord<T>;
}

/** The named filter that the page's url asks for, e.g. "pending" for ?filter=pending, or "". */
function filterOfPageUrl(): string {
  return new URLSearchParams(window.location.search).get("filter")?.trim() ?? "";
}

/** How long to wait after the last keystroke of a search before it is requested, in milliseconds. */
export const SEARCH_DELAY_MS = 300;

// throttle duration for requerying to prevent excessive backend requests
const REQUERY_THROTTLE_MS = 2000;

export default function TabbedListView<TObject>({
  sessionContext,
  tabbedListViewContext,
}: TabbedListViewProps<TObject>) {
  const tabs = tabbedListViewContext.tabs;
  const tabKeys = useMemo(() => tabs.map((tab) => tab.key), [tabs]);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // list state management for owned/shared object lists.
  //
  // We'll be optimistic, and hope that cached data is available to populate
  // these before the async load completes. If not, then we'll show loading
  // skeletons until the load finishes and populates these states. Note that
  // the skeletons make use of cookie-backed counts to size themselves to whatever
  // they'd most recently been, which should help prevent jarring resizing when
  // the real data loads.
  // A list is loading until the first load completes, unless its cache already has its objects.
  // The cache holds every page, ordering and filter that the list showed, but no search, in
  // localStorage, scoped by the session, so that a list paints at once on a return visit, in a new
  // browser tab, and when paging back. See ../../lib/cache.
  // the named filter of both tabs, from the page's url.
  const [filter, setFilter] = useState(filterOfPageUrl);
  const scope = useMemo(() => sessionScope(sessionContext), [sessionContext]);
  const cacheKey = useCallback(
    (tab: TabKey, page: number, tabOrdering: string, tabFilter: string) =>
      makeCacheKey(sessionContext.ApiUrl, tab, { page, ordering: tabOrdering, filter: tabFilter }, scope),
    [sessionContext, scope],
  );
  const [lists, setLists] = useState<TabRecord<TabList>>(() =>
    tabRecord(tabKeys, (tab) => {
      const cached = readCache<unknown>(cacheKey(tab, 1, "", filter));
      return {
        objects: cached?.objects ?? [],
        isLoading: cached === null,
        isRefreshing: cached !== null,
        pagination: cached?.pagination ?? null,
      };
    }),
  );

  // each tab's requested page, and the search of both tabs. searchInput is the search as it is
  // typed, and search follows it once typing pauses, so that every keystroke is not a request.
  const [pages, setPages] = useState<TabRecord<number>>(() => tabRecord(tabKeys, () => 1));
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  // the column that sorts both tabs, as the list api names it, e.g. "-name". Empty for its default order.
  const [ordering, setOrdering] = useState("");

  // only the latest request of a tab is shown, when several are in flight, e.g. when the user
  // pages quickly, or a requery and a page change overlap.
  const latestRequest = useRef<TabRecord<number>>(tabRecord(tabKeys, () => 0));

  // for sizing the skeleton loaders that are rendered if no cached data is available
  const maxGhostRows = 25;
  const clamp = (val: number, min: number, max: number) => Math.max(min, Math.min(max, val));
  const ghostCount = (tab: TabKey) => clamp(getCookieForUrl(sessionContext.ApiUrl + tab + "/") || 6, 0, maxGhostRows);

  const [activeTab, setActiveTab] = useState<TabKey>(() => tabKeys[0]);
  const [viewMode, _setViewMode] = useState<ViewMode>(() => {
    const saved = sessionStorage.getItem("viewMode");
    return saved === "thumbnail" ? "thumbnail" : "list";
  });
  const setViewMode = (mode: ViewMode) => {
    _setViewMode(mode);
    sessionStorage.setItem("viewMode", mode);
  };

  const requeryRef = useRef<number | null>(null);

  // load a page of a tab's objects that match the search, in the ordering.
  // invalidateCache: whether the backend (Django-Redis) cache should be invalidated, e.g. after a
  // clone, rename or delete. It is a parameter, rather than state, so that a requery's load sees it.
  // isActive: whether the results are still wanted; a load that a newer one replaced, or that
  // finishes after the component unmounts, is ignored.
  const loadTab = useCallback(
    (
      tab: TabKey,
      page: number,
      tabSearch: string,
      tabOrdering: string,
      tabFilter: string,
      invalidateCache: boolean,
      isActive: () => boolean = () => true,
    ): Promise<void> => {
      const request = (latestRequest.current[tab] ?? 0) + 1;
      latestRequest.current[tab] = request;
      // show the page from the cache at once, if it holds it, and its loading skeleton otherwise.
      const key = cacheKey(tab, page, tabOrdering, tabFilter);
      const cached = tabSearch ? null : readCache<unknown>(key);
      setLists((prev) => ({
        ...prev,
        [tab]: cached
          ? { objects: cached.objects, pagination: cached.pagination, isLoading: false, isRefreshing: true }
          : { ...prev[tab], isLoading: true, isRefreshing: false },
      }));
      console.debug(
        `${loggerPrefix} loadTab() Loading ${tab} objects, page=${page}, search="${tabSearch}", ordering="${tabOrdering}", filter="${tabFilter}", invalidateCache=${invalidateCache}`,
      );
      return load<unknown>(sessionContext, invalidateCache, tab, setErrorMessage, {
        page,
        search: tabSearch,
        ordering: tabOrdering,
        filter: tabFilter,
      }).then(({ objects, pagination }) => {
        if (!isActive() || request !== latestRequest.current[tab]) return;
        console.debug(`${loggerPrefix} loadTab() received ${tab} objects:`, objects, pagination);
        setLists((prev) => ({ ...prev, [tab]: { objects, isLoading: false, isRefreshing: false, pagination } }));
        if (!tabSearch && pagination) {
          writeCache(key, objects, pagination);
        }
      });
    },
    [sessionContext, cacheKey],
  );

  const onPage = (page: number) => {
    console.debug(`${loggerPrefix} onPage() going to page ${page} of the ${activeTab} objects`);
    setPages((prev) => ({ ...prev, [activeTab]: page }));
  };

  // sort both tabs by a column, from their first pages.
  const onSort = (requested: string) => {
    console.debug(`${loggerPrefix} onSort() sorting by "${requested}", reloading the first page of each tab`);
    setPages(tabRecord(tabKeys, () => 1));
    setOrdering(requested);
  };

  // show every object again: remove the filter, from the list and from the page's url.
  const clearFilter = () => {
    console.debug(
      `${loggerPrefix} clearFilter() removing the "${filter}" filter, reloading the first page of each tab`,
    );
    const url = new URL(window.location.href);
    url.searchParams.delete("filter");
    window.history.replaceState(window.history.state, "", url);
    setPages(tabRecord(tabKeys, () => 1));
    setFilter("");
  };

  // request the search once typing pauses, from the first page of each tab.
  useEffect(() => {
    const timer = setTimeout(() => {
      const requested = searchInput.trim();
      if (requested === search) return;
      console.debug(`${loggerPrefix} search changed to "${requested}", reloading the first page of each tab`);
      setPages(tabRecord(tabKeys, () => 1));
      setSearch(requested);
    }, SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [searchInput, search, tabKeys]);

  const onRequery = () => {
    console.debug(`${loggerPrefix} onRequery() called, reloading data and invalidating the backend cache`);
    if (tabKeys.some((tab) => lists[tab]?.isLoading)) {
      return;
    }
    // throttle to prevent excessive requerying if user clicks multiple times in a short span
    const now = Date.now();
    if (requeryRef.current && now - requeryRef.current < REQUERY_THROTTLE_MS) {
      return;
    }
    requeryRef.current = now;
    tabKeys.forEach((tab) => void loadTab(tab, pages[tab], search, ordering, filter, true));
  };

  // whether the component is mounted: the results of a load that finishes after it unmounts are ignored.
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  // each tab's last requested page, search and ordering, and the loadTab that requested them, so
  // that a tab is loaded again only when its own request changes, or the session context does.
  const requested = useRef<{ loadTab: typeof loadTab | null; params: Partial<Record<TabKey, string>> }>({
    loadTab: null,
    params: {},
  });

  // load each tab on mount, whenever the session context changes, and whenever its page, the
  // search or the ordering changes. The cached objects, if any, are shown at once (see the state initializers
  // above), and replaced by the freshly loaded ones.
  useEffect(() => {
    if (requested.current.loadTab !== loadTab) {
      requested.current = { loadTab, params: {} };
    }
    tabKeys.forEach((tab) => {
      const page = pages[tab] ?? 1;
      const params = JSON.stringify([page, search, ordering, filter]);
      if (requested.current.params[tab] === params) return;
      requested.current.params[tab] = params;
      void loadTab(tab, page, search, ordering, filter, false, () => mounted.current);
    });
  }, [loadTab, tabKeys, pages, search, ordering, filter]);

  if (errorMessage) {
    return (
      <div className="alert alert-danger" role="alert">
        {errorMessage}
      </div>
    );
  }

  const tab = tabs.find((item) => item.key === activeTab) ?? tabs[0];
  const list = lists[tab.key];
  const ghostRows = ghostCount(tab.key);
  // the active tab's views: its own, or the list's. A tab's objects are those that its views show.
  const listViewOf = (key: TabKey) => tabs.find((item) => item.key === key)?.ListView ?? tabbedListViewContext.ListView;
  const ListView = listViewOf(tab.key) as React.ComponentType<ListViewBaseProps<unknown, SessionContext>>;
  const CardView = (tab.CardView ?? tabbedListViewContext.CardView) as React.ComponentType<
    CardViewBaseProps<unknown, SessionContext>
  >;
  const objectTypeName = tab.objectTypeName ?? tabbedListViewContext.objectTypeName;
  // the columns that the list api can sort by. The response of any tab with the same list view
  // says, so that the headers of a tab are sortable even before its own first response.
  const sameView = tabKeys.filter((key) => listViewOf(key) === listViewOf(tab.key));
  const pagination = list.pagination ?? sameView.map((key) => lists[key].pagination).find(Boolean);
  const sortFields = pagination?.sortFields ?? [];
  const sorting: Sorting = { ordering, sortFields, onSort };
  // the filter that applies: the api ignores, and reports as "", a filter that it doesn't offer.
  const appliedFilter = list.pagination ? (list.pagination.filter ?? filter) : filter;
  const filterLabel = tabbedListViewContext.filters?.[appliedFilter] ?? appliedFilter;

  return (
    <div className="pt-5 pb-5 card card-flush h-xl-100">
      <div className="card-header rounded align-items-start ps-3" data-bs-theme="light">
        <TabNav activeTab={tab.key} onTabChange={setActiveTab} tabs={tabs} />
      </div>
      <div className="m-0 p-0 card-body list-view">
        <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 pe-3">
          <div className="d-flex flex-wrap align-items-center gap-3">
            <ToggleButton viewMode={viewMode} setViewMode={setViewMode} />
            {list.isRefreshing && (
              <span
                className="spinner-border spinner-border-sm text-primary opacity-75"
                role="status"
                title={gettext("Refreshing")}
                aria-label={gettext("Refreshing")}
              ></span>
            )}
            {appliedFilter && (
              <span className="badge badge-light-primary fs-7 fw-semibold d-inline-flex align-items-center gap-2 py-2 ps-3 pe-2">
                {
                  // Translators: the label of the filter that narrows a list, e.g. "Pending deployment".
                  interpolate(gettext("Showing: %(filter)s"), { filter: filterLabel })
                }
                <button
                  type="button"
                  className="btn btn-icon btn-sm h-20px w-20px btn-active-light-primary"
                  aria-label={gettext("Show all")}
                  title={gettext("Show all")}
                  onClick={clearFilter}
                >
                  <i className="ki-outline ki-cross fs-6 text-primary"></i>
                </button>
              </span>
            )}
          </div>
          <SearchBox
            value={searchInput}
            onChange={setSearchInput}
            placeholder={
              // Translators: objects is the plural of a resource kind's name, e.g. secrets.
              interpolate(gettext("Search %(objects)s"), { objects: `${objectTypeName}s` })
            }
          />
        </div>

        {viewMode === "list" ? (
          <ListView
            key={tab.key}
            isLoading={list.isLoading}
            ghostRows={ghostRows}
            sessionContext={sessionContext}
            objects={list.objects}
            onRequery={onRequery}
            sorting={sorting}
          />
        ) : (
          <CardView key={tab.key} sessionContext={sessionContext} objects={list.objects} onRequery={onRequery} />
        )}

        {list.pagination && list.pagination.count > 0 && (
          <PaginationControls pagination={list.pagination} disabled={list.isLoading} onPage={onPage} />
        )}
      </div>
    </div>
  );
}
