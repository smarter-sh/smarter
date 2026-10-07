/**
 * TabbedListView React Component
 *
 * Displays a tabbed interface for viewing llmclients owned by the current user
 * and llmclients shared with the user.
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
 * - isLoadingOwned: Loading state for owned llmclients.
 * - isLoadingShared: Loading state for shared llmclients.
 * - errorMessage: Error text for failed requests.
 * - userListObjects: Owned llmclient list.
 * - sharedListObjects: Shared llmclient list.
 * - viewMode: Current display mode ("list" or "thumbnail").
 * - activeTab: Current tab ("user" or "shared").
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
 * - Writes successful fetch results back to the cache so the next initial page load
 *   can show recent data without waiting on the network.
 *
 * Usage:
 * <TabbedListView sessionContext={sessionContext} />
 */
import { useCallback, useEffect, useRef, useState } from "react";

import type { SessionContext, TabbedViewContext, TabKey } from "../../lib/Types";
import { load } from "../../lib/load";
import { loggerPrefix } from "../../lib/const";
import { makeCacheKey, readCache, writeCache } from "../../lib/cache";

import ToggleButton from "../ToggleButton";
import type { ViewMode } from "../ToggleButton";

import { getCookieForUrl } from "./cookie";
import { TabNav } from "./TabNavigation";

type TabbedListViewProps<TObject> = {
  sessionContext: SessionContext;
  tabbedListViewContext: TabbedViewContext<TObject>;
};

export default function TabbedListView<TObject>({
  sessionContext,
  tabbedListViewContext,
}: TabbedListViewProps<TObject>) {
  // cache keys for session-based local caching of owned/shared lists
  // to improve perceived load times on repeat visits
  const sharedListCacheKey = makeCacheKey(sessionContext.ApiUrl, "shared");
  const ownedListCacheKey = makeCacheKey(sessionContext.ApiUrl, "owned");

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
  const [isLoadingOwned, setIsLoadingOwned] = useState<boolean>(() => readCache<TObject>(ownedListCacheKey) === null);
  const [isLoadingShared, setIsLoadingShared] = useState<boolean>(
    () => readCache<TObject>(sharedListCacheKey) === null,
  );
  const [userListObjects, setUserListObjects] = useState<TObject[]>(() => readCache<TObject>(ownedListCacheKey) || []);
  const [sharedListObjects, setSharedListObjects] = useState<TObject[]>(
    () => readCache<TObject>(sharedListCacheKey) || [],
  );

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

  // throttle duration for requerying to prevent excessive backend requests
  const REQUERY_THROTTLE_MS = 2000;
  const requeryRef = useRef<number | null>(null);

  // load both owned and shared lists, on mount, whenever the session context changes, and on requery.
  // invalidateCache: whether the backend (Django-Redis) cache should be invalidated, e.g. after a
  // clone, rename or delete. It is a parameter, rather than state, so that a requery's load sees it.
  // isActive: whether the results are still wanted; a load that a newer one replaced, or that
  // finishes after the component unmounts, is ignored.
  const handleLoad = useCallback(
    (invalidateCache: boolean, isActive: () => boolean = () => true): Promise<void> => {
      console.debug(
        `${loggerPrefix} handleLoad() Loading owned and shared objects with invalidateCache=${invalidateCache}`,
      );
      return load<TObject>(sessionContext, invalidateCache, "owned", setErrorMessage)
        .then((ownedObjects) => {
          if (!isActive()) return;
          console.debug(
            `${loggerPrefix} handleLoad() received owned objects, calling setUserListObjects() and writeCache():`,
            ownedObjects,
          );
          setUserListObjects(ownedObjects);
          writeCache(ownedListCacheKey, ownedObjects);
          setIsLoadingOwned(false);
          return load<TObject>(sessionContext, invalidateCache, "shared", setErrorMessage);
        })
        .then((sharedObjects) => {
          if (!sharedObjects || !isActive()) return;
          console.debug(
            `${loggerPrefix} handleLoad() received shared objects, calling setSharedListObjects() and writeCache():`,
            sharedObjects,
          );
          setSharedListObjects(sharedObjects);
          writeCache(sharedListCacheKey, sharedObjects);
          setIsLoadingShared(false);
        });
    },
    [sessionContext, ownedListCacheKey, sharedListCacheKey],
  );

  const onRequery = () => {
    console.debug(`${loggerPrefix} onRequery() called, reloading data and invalidating the backend cache`);
    if (isLoadingOwned || isLoadingShared) {
      return;
    }
    // throttle to prevent excessive requerying if user clicks multiple times in a short span
    const now = Date.now();
    if (requeryRef.current && now - requeryRef.current < REQUERY_THROTTLE_MS) {
      return;
    }
    requeryRef.current = now;
    void handleLoad(true);
  };

  // the cached objects, if any, are shown at once (see the state initializers above), and
  // replaced by the freshly loaded ones.
  useEffect(() => {
    console.debug(
      `${loggerPrefix} useEffect() triggered on mount/sessionContext change, loading data with handleLoad()`,
    );
    let active = true;
    void handleLoad(false, () => active);
    return () => {
      active = false;
    };
  }, [handleLoad]);

  if (errorMessage) {
    return (
      <div className="alert alert-danger" role="alert">
        {errorMessage}
      </div>
    );
  }

  return (
    <div className="pt-5 pb-5 card card-flush h-xl-100">
      <div className="card-header rounded align-items-start ps-3" data-bs-theme="light">
        <TabNav activeTab={activeTab} onTabChange={setActiveTab} tabs={tabbedListViewContext.tabs} />
      </div>
      <div className="m-0 p-0 card-body list-view">
        <ToggleButton viewMode={viewMode} setViewMode={setViewMode} />

        {activeTab === "owned" ? (
          viewMode === "list" ? (
            <tabbedListViewContext.ListView
              isLoading={isLoadingOwned}
              ghostRows={userGhostCount}
              sessionContext={sessionContext}
              objects={userListObjects}
              onRequery={onRequery}
            />
          ) : (
            <tabbedListViewContext.CardView
              sessionContext={sessionContext}
              objects={userListObjects}
              onRequery={onRequery}
            />
          )
        ) : viewMode === "list" ? (
          <tabbedListViewContext.ListView
            isLoading={isLoadingShared}
            ghostRows={sharedGhostCount}
            sessionContext={sessionContext}
            objects={sharedListObjects}
            onRequery={onRequery}
          />
        ) : (
          <tabbedListViewContext.CardView
            sessionContext={sessionContext}
            objects={sharedListObjects}
            onRequery={onRequery}
          />
        )}
      </div>
    </div>
  );
}
