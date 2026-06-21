/**
 * TabbedListView React Component
 *
 * Displays a tabbed interface for viewing llm_clients owned by the current user
 * and llm_clients shared with the user.
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
 * - Loads owned and shared llm_client lists from the backend using session context.
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
 * - isLoadingOwned: Loading state for owned llm_clients.
 * - isLoadingShared: Loading state for shared llm_clients.
 * - errorMessage: Error text for failed requests.
 * - userListObjects: Owned llm_client list.
 * - sharedListObjects: Shared llm_client list.
 * - invalidateCacheFlag: Indicates whether backend cache should be invalidated on load.
 * - viewMode: Current display mode ("list" or "thumbnail").
 * - activeTab: Current tab ("user" or "shared").
 *
 * Internal Helpers:
 * - getCookie: Reads cookie values used for skeleton sizing.
 * - load (from ./load): Fetches llm_client data and updates state via setters.
 *
 * Page Rendering Performance and Caching behavior:
 * - Improves the perceived load time by rendering cached results immediately when
 *   available while a fresh backend fetch is still in flight. It is not uncommon
 *   for the backend response to take up to 1-2 seconds, so this is important from
 *   a UX perspective.
 * - Reads the most recent owned/shared llm_client results from sessionStorage on mount,
 *   keyed by API URL and tab.
 * - Writes successful fetch results back to the cache so the next initial page load
 *   can show recent data without waiting on the network.
 *
 * Usage:
 * <TabbedListView sessionContext={sessionContext} />
 */
import { useEffect, useRef, useState } from "react";

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

export default function TabbedListView<TObject>({ sessionContext, tabbedListViewContext }: TabbedListViewProps<TObject>) {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // list state management for owned/shared object lists.
  const [isLoadingOwned, setIsLoadingOwned] = useState<boolean>(true);
  const [isLoadingShared, setIsLoadingShared] = useState<boolean>(true);
  const [userListObjects, setUserListObjects] = useState<TObject[]>([]);
  const [sharedListObjects, setSharedListObjects] = useState<TObject[]>([]);

  // cache keys for session-based local caching of owned/shared lists
  // to improve perceived load times on repeat visits
  const sharedListCacheKey = makeCacheKey(sessionContext.ApiUrl, "shared");
  const ownedListCacheKey = makeCacheKey(sessionContext.ApiUrl, "owned");

  // controls whether to invalidate backend (Django-Redis) cache on next load
  // toggled by requery action.
  const [invalidateCacheFlag, setInvalidateCacheFlag] = useState<boolean>(false);

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

  // for sizing the skeleton loaders that are rendered while data is loading
  const maxGhostRows = 25;
  const clamp = (val: number, min: number, max: number) => Math.max(min, Math.min(max, val));
  const userGhostCount = clamp(getCookieForUrl(sessionContext.ApiUrl + "owned/") || 6, 0, maxGhostRows);
  const sharedGhostCount = clamp(getCookieForUrl(sessionContext.ApiUrl + "shared/") || 6, 0, maxGhostRows);

  // initiate load of both owned and shared lists on component mount and whenever session context changes
  const handleLoad = async () => {
    console.debug(`${loggerPrefix} handleLoad() Loading owned and shared objects with invalidateCacheFlag=${invalidateCacheFlag}`);

    const ownedObjects = await load<TObject>(sessionContext, invalidateCacheFlag, "owned", setErrorMessage);
    console.debug(`${loggerPrefix} handleLoad() received owned objects, calling setUserListObjects() and writeCache():`, ownedObjects);
    setUserListObjects(ownedObjects);
    writeCache(ownedListCacheKey, ownedObjects);
    console.debug(`${loggerPrefix} handleLoad() setting isLoadingOwned to false`);
    setIsLoadingOwned(false);

    const sharedObjects = await load<TObject>(
      sessionContext,
      invalidateCacheFlag,
      "shared",
      setErrorMessage,
    );
    console.debug(`${loggerPrefix} handleLoad() received shared objects, calling setSharedListObjects() and writeCache():`, sharedObjects);
    setSharedListObjects(sharedObjects);
    writeCache(sharedListCacheKey, sharedObjects);
    console.debug(`${loggerPrefix} handleLoad() setting isLoadingShared to false`);
    setIsLoadingShared(false);
  };

  const onRequery = () => {
    console.debug(`${loggerPrefix} onRequery() called, setting invalidateCacheFlag to true and reloading data`);
    setInvalidateCacheFlag(true);
    if (isLoadingOwned || isLoadingShared) {
      return;
    }
    // throttle to prevent excessive requerying if user clicks multiple times in a short span
    const now = Date.now();
    if (requeryRef.current && now - requeryRef.current < REQUERY_THROTTLE_MS) {
      return;
    }
    requeryRef.current = now;
    handleLoad();
  };

  useEffect(() => {
    console.debug(`${loggerPrefix} useEffect() triggered on mount/sessionContext change, checking cache and loading data with handleLoad()`);

    const ownedCached = readCache(ownedListCacheKey);
    if (ownedCached) {
      console.debug(`${loggerPrefix} useEffect() found cached owned objects, calling setUserListObjects(), setting isLoadingOwned to false:`, ownedCached);
      setUserListObjects(ownedCached);
      setIsLoadingOwned(false);
    } else {
      console.debug(`${loggerPrefix} useEffect() did not find cached owned objects, setting isLoadingOwned to true`);
      setIsLoadingOwned(true);
    }


    const sharedCached = readCache(sharedListCacheKey);
    if (sharedCached) {
      console.debug(`${loggerPrefix} useEffect() found cached shared objects, calling setSharedListObjects(), setting isLoadingShared to false:`, sharedCached);
      setSharedListObjects(sharedCached);
      setIsLoadingShared(false);
    } else {
      console.debug(`${loggerPrefix} useEffect() did not find cached shared objects, setting isLoadingShared to true`);
      setIsLoadingShared(true);
    }

    void handleLoad();
  }, [sessionContext]);

  if (errorMessage) {
    return <div className="alert alert-danger">{errorMessage}</div>;
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
            <tabbedListViewContext.CardView sessionContext={sessionContext} objects={userListObjects} onRequery={onRequery} />
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
          <tabbedListViewContext.CardView sessionContext={sessionContext} objects={sharedListObjects} onRequery={onRequery} />
        )}
      </div>
    </div>
  );
}
