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
 * - errorMessage: Error text for failed requests.
 * - viewMode: Current display mode ("list" or "thumbnail").
 * - activeTab: Current tab ("owned" or "shared").
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
 * - Writes successful fetch results of each tab's first page, without a search, back to the
 *   cache so the next initial page load can show recent data without waiting on the network.
 *
 * Usage:
 * <TabbedListView sessionContext={sessionContext} />
 */
import { useCallback, useEffect, useRef, useState } from "react";

import type { Pagination, SessionContext, TabbedViewContext, TabKey } from "../../lib/Types";
import { load } from "../../lib/load";
import { loggerPrefix } from "../../lib/const";
import { makeCacheKey, readCache, writeCache } from "../../lib/cache";

import ToggleButton from "../ToggleButton";
import type { ViewMode } from "../ToggleButton";

import { getCookieForUrl } from "./cookie";
import { PaginationControls } from "./PaginationControls";
import { SearchBox } from "./SearchBox";
import { TabNav } from "./TabNavigation";

type TabbedListViewProps<TObject> = {
  sessionContext: SessionContext;
  tabbedListViewContext: TabbedViewContext<TObject>;
};

type TabList<TObject> = {
  objects: TObject[];
  isLoading: boolean;
  pagination: Pagination | null;
};

type TabRecord<T> = Record<TabKey, T>;

const TAB_KEYS: TabKey[] = ["owned", "shared"];

/** How long to wait after the last keystroke of a search before it is requested, in milliseconds. */
export const SEARCH_DELAY_MS = 300;

/** The lists, with those of tabs loading, so that they show their loading skeleton while they load another page, or another search. */
function withLoading<TObject>(lists: TabRecord<TabList<TObject>>, tabs: TabKey[]): TabRecord<TabList<TObject>> {
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
  // cache keys for session-based local caching of each tab's first page, without a search,
  // to improve perceived load times on repeat visits
  const cacheKeys: TabRecord<string> = {
    owned: makeCacheKey(sessionContext.ApiUrl, "owned"),
    shared: makeCacheKey(sessionContext.ApiUrl, "shared"),
  };

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
  const [lists, setLists] = useState<TabRecord<TabList<TObject>>>(() => {
    const initialList = (cacheKey: string): TabList<TObject> => {
      const cached = readCache<TObject>(cacheKey);
      return { objects: cached || [], isLoading: cached === null, pagination: null };
    };
    return { owned: initialList(cacheKeys.owned), shared: initialList(cacheKeys.shared) };
  });

  // each tab's requested page, and the search of both tabs. searchInput is the search as it is
  // typed, and search follows it once typing pauses, so that every keystroke is not a request.
  const [pages, setPages] = useState<TabRecord<number>>({ owned: 1, shared: 1 });
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  // only the latest request of a tab is shown, when several are in flight, e.g. when the user
  // pages quickly, or a requery and a page change overlap.
  const latestRequest = useRef<TabRecord<number>>({ owned: 0, shared: 0 });

  // for sizing the skeleton loaders that are rendered if no cached data is available
  const maxGhostRows = 25;
  const clamp = (val: number, min: number, max: number) => Math.max(min, Math.min(max, val));
  const userGhostCount = clamp(getCookieForUrl(sessionContext.ApiUrl + "owned/") || 6, 0, maxGhostRows);
  const sharedGhostCount = clamp(getCookieForUrl(sessionContext.ApiUrl + "shared/") || 6, 0, maxGhostRows);

  // define 2-tab layout with cookie-based persistent active tab state
  const [activeTab, setActiveTab] = useState<TabKey>("owned");
  const [viewMode, _setViewMode] = useState<ViewMode>(() => {
    const saved = sessionStorage.getItem("viewMode");
    return saved === "thumbnail" ? "thumbnail" : "list";
  });
  const setViewMode = (mode: ViewMode) => {
    _setViewMode(mode);
    sessionStorage.setItem("viewMode", mode);
  };

  const requeryRef = useRef<number | null>(null);

  // load a page of a tab's objects that match the search.
  // invalidateCache: whether the backend (Django-Redis) cache should be invalidated, e.g. after a
  // clone, rename or delete. It is a parameter, rather than state, so that a requery's load sees it.
  // isActive: whether the results are still wanted; a load that a newer one replaced, or that
  // finishes after the component unmounts, is ignored.
  const loadTab = useCallback(
    (
      tab: TabKey,
      page: number,
      tabSearch: string,
      invalidateCache: boolean,
      isActive: () => boolean = () => true,
    ): Promise<void> => {
      const request = ++latestRequest.current[tab];
      console.debug(
        `${loggerPrefix} loadTab() Loading ${tab} objects, page=${page}, search="${tabSearch}", invalidateCache=${invalidateCache}`,
      );
      return load<TObject>(sessionContext, invalidateCache, tab, setErrorMessage, { page, search: tabSearch }).then(
        ({ objects, pagination }) => {
          if (!isActive() || request !== latestRequest.current[tab]) return;
          console.debug(`${loggerPrefix} loadTab() received ${tab} objects:`, objects, pagination);
          setLists((prev) => ({ ...prev, [tab]: { objects, isLoading: false, pagination } }));
          if (page === 1 && !tabSearch) {
            writeCache(makeCacheKey(sessionContext.ApiUrl, tab), objects);
          }
        },
      );
    },
    [sessionContext],
  );

  const onPage = (page: number) => {
    console.debug(`${loggerPrefix} onPage() going to page ${page} of the ${activeTab} objects`);
    setLists((prev) => withLoading(prev, [activeTab]));
    setPages((prev) => ({ ...prev, [activeTab]: page }));
  };

  // request the search once typing pauses, from the first page of each tab.
  useEffect(() => {
    const timer = setTimeout(() => {
      const requested = searchInput.trim();
      if (requested === search) return;
      console.debug(`${loggerPrefix} search changed to "${requested}", reloading the first page of each tab`);
      setLists((prev) => withLoading(prev, TAB_KEYS));
      setPages({ owned: 1, shared: 1 });
      setSearch(requested);
    }, SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [searchInput, search]);

  const onRequery = () => {
    console.debug(`${loggerPrefix} onRequery() called, reloading data and invalidating the backend cache`);
    if (lists.owned.isLoading || lists.shared.isLoading) {
      return;
    }
    // throttle to prevent excessive requerying if user clicks multiple times in a short span
    const now = Date.now();
    if (requeryRef.current && now - requeryRef.current < REQUERY_THROTTLE_MS) {
      return;
    }
    requeryRef.current = now;
    TAB_KEYS.forEach((tab) => void loadTab(tab, pages[tab], search, true));
  };

  // load each tab on mount, whenever the session context changes, and whenever its page or the
  // search changes. The cached objects, if any, are shown at once (see the state initializers
  // above), and replaced by the freshly loaded ones.
  useEffect(() => {
    let active = true;
    void loadTab("owned", pages.owned, search, false, () => active);
    return () => {
      active = false;
    };
  }, [loadTab, pages.owned, search]);

  useEffect(() => {
    let active = true;
    void loadTab("shared", pages.shared, search, false, () => active);
    return () => {
      active = false;
    };
  }, [loadTab, pages.shared, search]);

  if (errorMessage) {
    return (
      <div className="alert alert-danger" role="alert">
        {errorMessage}
      </div>
    );
  }

  const list = lists[activeTab];
  const ghostRows = activeTab === "owned" ? userGhostCount : sharedGhostCount;

  return (
    <div className="pt-5 pb-5 card card-flush h-xl-100">
      <div className="card-header rounded align-items-start ps-3" data-bs-theme="light">
        <TabNav activeTab={activeTab} onTabChange={setActiveTab} tabs={tabbedListViewContext.tabs} />
      </div>
      <div className="m-0 p-0 card-body list-view">
        <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 pe-3">
          <ToggleButton viewMode={viewMode} setViewMode={setViewMode} />
          <SearchBox
            value={searchInput}
            onChange={setSearchInput}
            placeholder={`Search ${tabbedListViewContext.objectTypeName}s`}
          />
        </div>

        {viewMode === "list" ? (
          <tabbedListViewContext.ListView
            key={activeTab}
            isLoading={list.isLoading}
            ghostRows={ghostRows}
            sessionContext={sessionContext}
            objects={list.objects}
            onRequery={onRequery}
          />
        ) : (
          <tabbedListViewContext.CardView
            key={activeTab}
            sessionContext={sessionContext}
            objects={list.objects}
            onRequery={onRequery}
          />
        )}

        {list.pagination && list.pagination.count > 0 && (
          <PaginationControls pagination={list.pagination} disabled={list.isLoading} onPage={onPage} />
        )}
      </div>
    </div>
  );
}
