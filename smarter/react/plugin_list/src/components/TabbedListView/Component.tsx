/**
 * TabbedListView React Component
 *
 * Displays a tabbed interface for viewing plugins owned by the current user
 * and plugins shared with the user.
 *
 * Tabs:
 * - Your Plugins
 * - Shared Plugins
 *
 * View Modes:
 * - List
 * - Thumbnail card
 *
 * Features:
 * - Loads owned and shared plugin lists from the backend using session context.
 * - Shows loading and error states during fetches.
 * - Allows switching between list and card views.
 * - Persists the selected view mode in localStorage.
 * - Uses cookie-backed counts (owned/shared) to size loading skeleton rows.
 * - Supports requery with cache invalidation.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context used for requests.
 *
 * State:
 * - isLoadingOwned: Loading state for owned plugins.
 * - isLoadingShared: Loading state for shared plugins.
 * - errorMessage: Error text for failed requests.
 * - userListObjects: Owned plugin list.
 * - sharedListObjects: Shared plugin list.
 * - invalidateCacheFlag: Indicates whether backend cache should be invalidated on load.
 * - viewMode: Current display mode ("list" or "thumbnail").
 * - activeTab: Current tab ("user" or "shared").
 *
 * Internal Helpers:
 * - getCookie: Reads cookie values used for skeleton sizing.
 * - load (from ./load): Fetches plugin data and updates state via setters.
 *
 * Usage:
 * <TabbedListView sessionContext={sessionContext} />
 */
import { useEffect, useRef, useState } from "react";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";
import ToggleButton from "@/components/ToggleButton";
import type { ViewMode } from "@/components/ToggleButton";

import type { Plugin, SessionContext, TabKey } from "@/lib/Types";
import { getCookie } from "./cookie";
import { TabNav } from "./TabNavigation";
import { load } from "./load";
import "./styles.css";

export default function TabbedListView({ sessionContext }: { sessionContext: SessionContext }) {
  console.debug("Rendering TabbedListView with sessionContext:", sessionContext);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // list state management for owned/shared object lists.
  const [isLoadingOwned, setIsLoadingOwned] = useState<boolean>(true);
  const [isLoadingShared, setIsLoadingShared] = useState<boolean>(true);
  const [userListObjects, setUserListObjects] = useState<Plugin[]>([]);
  const [sharedListObjects, setSharedListObjects] = useState<Plugin[]>([]);

  // controls whether to invalidate backend cache on next load - toggled by requery action
  const [invalidateCacheFlag, setInvalidateCacheFlag] = useState<boolean>(false);

  // define 2-tab layout with cookie-based persistent active tab state
  const tabs: { key: TabKey; label: string }[] = [
    { key: "user", label: "Your Plugins" },
    { key: "shared", label: "Shared Plugins" },
  ];
  const [activeTab, setActiveTab] = useState<"user" | "shared">("user");
  const [viewMode, _setViewMode] = useState<ViewMode>(() => {
    const saved = localStorage.getItem("viewMode");
    return saved === "thumbnail" ? "thumbnail" : "list";
  });
  const setViewMode = (mode: ViewMode) => {
    _setViewMode(mode);
    localStorage.setItem("viewMode", mode);
  };

  // throttle duration for requerying to prevent excessive backend requests
  const REQUERY_THROTTLE_MS = 2000;
  const requeryRef = useRef<number | null>(null);

  // for sizing the skeleton loaders that are rendered while data is loading
  const maxGhostRows = 25;
  const clamp = (val: number, min: number, max: number) => Math.max(min, Math.min(max, val));
  const userGhostCount = clamp(getCookie("owned", "plugin_count") || 6, 0, maxGhostRows);
  const sharedGhostCount = clamp(getCookie("shared", "plugin_count") || 6, 0, maxGhostRows);

  // initiate load of both owned and shared plugin lists on component mount and whenever session context changes
  const handleLoad = () => {
    load(sessionContext, invalidateCacheFlag, setUserListObjects, setIsLoadingOwned, "owned", setErrorMessage);
    load(sessionContext, invalidateCacheFlag, setSharedListObjects, setIsLoadingShared, "shared", setErrorMessage);
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
    handleLoad();
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
