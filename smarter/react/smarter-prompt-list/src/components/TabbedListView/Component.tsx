/**
 * TabbedListView React Component
 *
 * Displays a tabbed interface for viewing chatbots owned by the current user
 * and chatbots shared with the user.
 *
 * Tabs:
 * - Your Chatbots
 * - Shared Chatbots
 *
 * View Modes:
 * - List
 * - Thumbnail card
 *
 * Features:
 * - Loads owned and shared chatbot lists from the backend using session context.
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
 * - isLoadingOwned: Loading state for owned chatbots.
 * - isLoadingShared: Loading state for shared chatbots.
 * - errorMessage: Error text for failed requests.
 * - userListObjects: Owned chatbot list.
 * - sharedListObjects: Shared chatbot list.
 * - invalidateCacheFlag: Indicates whether backend cache should be invalidated on load.
 * - viewMode: Current display mode ("list" or "thumbnail").
 * - activeTab: Current tab ("user" or "shared").
 *
 * Internal Helpers:
 * - getCookie: Reads cookie values used for skeleton sizing.
 * - load (from ./load): Fetches chatbot data and updates state via setters.
 *
 * Page Rendering Performance and Caching behavior:
 * - Improves the perceived load time by rendering cached results immediately when
 *   available while a fresh backend fetch is still in flight. It is not uncommon
 *   for the backend response to take up to 1-2 seconds, so this is important from
 *   a UX perspective.
 * - Reads the most recent owned/shared chatbot results from sessionStorage on mount,
 *   keyed by API URL and tab.
 * - Writes successful fetch results back to the cache so the next initial page load
 *   can show recent data without waiting on the network.
 *
 * Usage:
 * <TabbedListView sessionContext={sessionContext} />
 */
import { useEffect, useRef, useState } from "react";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";
import ToggleButton from "@/components/ToggleButton";
import type { ViewMode } from "@/components/ToggleButton";

import type { Chatbot, SessionContext, TabKey } from "@/lib/Types";
import { getCookie } from "./cookie";
import { TabNav } from "./TabNavigation";
import { load } from "./load";
import { makeCacheKey, readCache, writeCache } from "./cache";
import "./styles.css";


export default function TabbedListView({ sessionContext }: { sessionContext: SessionContext }) {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // list state management for owned/shared object lists.
  const [isLoadingOwned, setIsLoadingOwned] = useState<boolean>(true);
  const [isLoadingShared, setIsLoadingShared] = useState<boolean>(true);
  const [userListObjects, setUserListObjects] = useState<Chatbot[]>([]);
  const [sharedListObjects, setSharedListObjects] = useState<Chatbot[]>([]);

  // cache keys for session-based local caching of owned/shared lists
  // to improve perceived load times on repeat visits
  const sharedListCacheKey = makeCacheKey(sessionContext.ApiUrl, "shared");
  const ownedListCacheKey = makeCacheKey(sessionContext.ApiUrl, "owned");

  // controls whether to invalidate backend (Django-Redis) cache on next load
  // toggled by requery action.
  const [invalidateCacheFlag, setInvalidateCacheFlag] = useState<boolean>(false);

  // define 2-tab layout with cookie-based persistent active tab state
  const tabs: { key: TabKey; label: string }[] = [
    { key: "user", label: "Your Chatbots" },
    { key: "shared", label: "Shared Chatbots" },
  ];
  const [activeTab, setActiveTab] = useState<"user" | "shared">("user");
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
  const userGhostCount = clamp(getCookie("owned", "chatbot_count") || 6, 0, maxGhostRows);
  const sharedGhostCount = clamp(getCookie("shared", "chatbot_count") || 6, 0, maxGhostRows);

  // initiate load of both owned and shared chatbot lists on component mount and whenever session context changes
  const handleLoad = async () => {
    const ownedObjects = await load(sessionContext, invalidateCacheFlag, setIsLoadingOwned, "owned", setErrorMessage);
    setUserListObjects(ownedObjects);
    writeCache(ownedListCacheKey, ownedObjects);

    const sharedObjects = await load(
      sessionContext,
      invalidateCacheFlag,
      setIsLoadingShared,
      "shared",
      setErrorMessage,
    );
    setSharedListObjects(sharedObjects);
    writeCache(sharedListCacheKey, sharedObjects);
  };

  const onRequery = () => {
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
    setIsLoadingOwned(true);
    setIsLoadingShared(true);
    handleLoad();
  };

  useEffect(() => {
    const ownedCached = readCache(ownedListCacheKey);
    if (ownedCached) setUserListObjects(ownedCached);

    const sharedCached = readCache(sharedListCacheKey);
    if (sharedCached) setSharedListObjects(sharedCached);

    void handleLoad();
  }, [sessionContext]);

  if (errorMessage) {
    return <div className="alert alert-danger">{errorMessage}</div>;
  }

  return (
    <div className="pt-5 pb-5 card card-flush h-xl-100">
      <div className="card-header rounded align-items-start ps-3" data-bs-theme="light">
        <TabNav activeTab={activeTab} onTabChange={setActiveTab} tabs={tabs} />
      </div>
      <div className="m-0 p-0 card-body list-view">
        <ToggleButton viewMode={viewMode} setViewMode={setViewMode} />

        {activeTab === "user" ? (
          viewMode === "list" ? (
            <ListView
              isLoading={isLoadingOwned}
              ghostRows={userGhostCount}
              sessionContext={sessionContext}
              objects={userListObjects}
              onRequery={onRequery}
            />
          ) : (
            <CardView sessionContext={sessionContext} objects={userListObjects} onRequery={onRequery} />
          )
        ) : viewMode === "list" ? (
          <ListView
            isLoading={isLoadingShared}
            ghostRows={sharedGhostCount}
            sessionContext={sessionContext}
            objects={sharedListObjects}
            onRequery={onRequery}
          />
        ) : (
          <CardView sessionContext={sessionContext} objects={sharedListObjects} onRequery={onRequery} />
        )}
      </div>
    </div>
  );
}
