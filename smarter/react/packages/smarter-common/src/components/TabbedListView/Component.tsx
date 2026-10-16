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
 * - Hydrates the UI from cached results before the initial fetch resolves.
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
 *   available while a fresh backend fetch is still in flight. It is not uncommon
 *   for the backend response to take up to 1-2 seconds, so this is important from
 *   a UX perspective.
 * - Reads the most recent owned/shared llmclient results from sessionStorage on mount,
 *   keyed by API URL and tab.
 * - Writes successful fetch results of each tab's first page, without a search or a sort, back to the
 *   cache so the next initial page load can show recent data without waiting on the network.
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
import { makeCacheKey, readCache, writeCache } from "../../lib/cache";

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
  pagination: Pagination | null;
};

type TabRecord<T> = Record<TabKey, T>;

/** A record with a value for each tab. */
function tabRecord<T>(tabKeys: TabKey[], value: (tab: TabKey) => T): TabRecord<T> {
  return Object.fromEntries(tabKeys.map((tab) => [tab, value(tab)])) as TabRecord<T>;
}

/** How long to wait after the last keystroke of a search before it is requested, in milliseconds. */
export const SEARCH_DELAY_MS = 300;

/** The lists, with those of tabs loading, so that they show their loading skeleton while they load another page, or another search. */
function withLoading(lists: TabRecord<TabList>, tabs: TabKey[]): TabRecord<TabList> {
  const retval = { ...lists };
  tabs.forEach((tab) => {
    retval[tab] = { ...lists[tab], isLoading: true };
  });
  return retval;
}

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
  // The cache keys are for session-based local caching of each tab's first page, without a search
  // or a sort, to improve perceived load times on repeat visits.
  const [lists, setLists] = useState<TabRecord<TabList>>(() =>
    tabRecord(tabKeys, (tab) => {
      const cached = readCache<unknown>(makeCacheKey(sessionContext.ApiUrl, tab));
      return { objects: cached || [], isLoading: cached === null, pagination: null };
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
      invalidateCache: boolean,
      isActive: () => boolean = () => true,
    ): Promise<void> => {
      const request = (latestRequest.current[tab] ?? 0) + 1;
      latestRequest.current[tab] = request;
      console.debug(
        `${loggerPrefix} loadTab() Loading ${tab} objects, page=${page}, search="${tabSearch}", ordering="${tabOrdering}", invalidateCache=${invalidateCache}`,
      );
      return load<unknown>(sessionContext, invalidateCache, tab, setErrorMessage, {
        page,
        search: tabSearch,
        ordering: tabOrdering,
      }).then(({ objects, pagination }) => {
        if (!isActive() || request !== latestRequest.current[tab]) return;
        console.debug(`${loggerPrefix} loadTab() received ${tab} objects:`, objects, pagination);
        setLists((prev) => ({ ...prev, [tab]: { objects, isLoading: false, pagination } }));
        if (page === 1 && !tabSearch && !tabOrdering) {
          writeCache(makeCacheKey(sessionContext.ApiUrl, tab), objects);
        }
      });
    },
    [sessionContext],
  );

  const onPage = (page: number) => {
    console.debug(`${loggerPrefix} onPage() going to page ${page} of the ${activeTab} objects`);
    setLists((prev) => withLoading(prev, [activeTab]));
    setPages((prev) => ({ ...prev, [activeTab]: page }));
  };

  // sort both tabs by a column, from their first pages.
  const onSort = (requested: string) => {
    console.debug(`${loggerPrefix} onSort() sorting by "${requested}", reloading the first page of each tab`);
    setLists((prev) => withLoading(prev, tabKeys));
    setPages(tabRecord(tabKeys, () => 1));
    setOrdering(requested);
  };

  // request the search once typing pauses, from the first page of each tab.
  useEffect(() => {
    const timer = setTimeout(() => {
      const requested = searchInput.trim();
      if (requested === search) return;
      console.debug(`${loggerPrefix} search changed to "${requested}", reloading the first page of each tab`);
      setLists((prev) => withLoading(prev, tabKeys));
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
    tabKeys.forEach((tab) => void loadTab(tab, pages[tab], search, ordering, true));
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
      const params = JSON.stringify([page, search, ordering]);
      if (requested.current.params[tab] === params) return;
      requested.current.params[tab] = params;
      void loadTab(tab, page, search, ordering, false, () => mounted.current);
    });
  }, [loadTab, tabKeys, pages, search, ordering]);

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

  return (
    <div className="pt-5 pb-5 card card-flush h-xl-100">
      <div className="card-header rounded align-items-start ps-3" data-bs-theme="light">
        <TabNav activeTab={tab.key} onTabChange={setActiveTab} tabs={tabs} />
      </div>
      <div className="m-0 p-0 card-body list-view">
        <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 pe-3">
          <ToggleButton viewMode={viewMode} setViewMode={setViewMode} />
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
