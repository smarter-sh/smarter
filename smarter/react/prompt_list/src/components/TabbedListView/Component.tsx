/**
 * TabbedListView React Component
 *
 * This component displays a tabbed interface for viewing chatbots associated with the current user and chatbots shared with the user.
 * It provides two main tabs: "Your Chatbots" and "Shared Chatbots". Each tab can be viewed in either a list or card format, toggled by the user.
 *
 * Features:
 * - Fetches chatbot data for both user and shared chatbots from the backend API using the provided session context.
 * - Displays loading and error states during data fetching.
 * - Allows switching between list and card views for each tab.
 * - Uses child components for rendering (ListView, CardView, ToggleButton, TabNav).
 * - Persists view mode preference in localStorage.
 * - Stores and retrieves chatbot counts in cookies for each tab (owned/shared) to optimize UI skeleton loading.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for fetching chatbot data.
 *
 * State:
 * - isLoading: Indicates if chatbot data is being loaded.
 * - errorMessage: Stores any error message from failed fetches.
 * - userChatbots: List of chatbots owned by the user.
 * - sharedChatbots: List of chatbots shared with the user.
 * - viewMode: Current view mode ("list" or "card").
 * - activeTab: Currently selected tab ("user" or "shared").
 *
 * Internal Helpers:
 * - setCookie: Persists chatbot count for a tab in a cookie.
 * - getCookie: Retrieves chatbot count from a cookie for a tab.
 * - load: Fetches chatbot data and updates state, using cookies for skeleton row counts.
 *
 * Usage:
 * <TabbedListView sessionContext={sessionContext} />
 *
 * The component expects all required context and API URLs to be provided via the sessionContext prop.
 */
import { useEffect, useState } from "react";
import { loggerPrefix } from "@/const";
import ListView from "@/components/ListView";
import CardView from "@/components/CardView";
import ToggleButton from "@/components/ToggleButton";
import type { ViewMode } from "@/components/ToggleButton";

import fetchDjangoUrl from "@/lib/django";
import type { Chatbot, SessionContext, UserProfile, TabKey } from "@/lib/Types";

import "./styles.css";

interface TabNavProps {
  activeTab: TabKey;
  onTabChange: (tab: TabKey) => void;
  tabs: { key: TabKey; label: string }[];
}

const TabNav: React.FC<TabNavProps> = ({ activeTab, onTabChange, tabs }) => (
  <ul className="nav nav-tabs">
    {Array.isArray(tabs) &&
      tabs.map((tab) => (
        <li className="nav-item" key={tab.key}>
          <button
            className={`nav-link${activeTab === tab.key ? " active" : ""}`}
            onClick={() => onTabChange(tab.key)}
            type="button"
          >
            {tab.label}
          </button>
        </li>
      ))}
  </ul>
);

interface TabbedListViewProps {
  sessionContext: SessionContext;
}

interface ChatbotListApiResponse {
  user: UserProfile;
  admin: UserProfile;
  chatbots: Chatbot[];
}

function TabbedListView({ sessionContext }: TabbedListViewProps) {
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [userChatbots, setUserChatbots] = useState<Chatbot[]>([]);
  const [sharedChatbots, setSharedChatbots] = useState<Chatbot[]>([]);
  const [viewMode, _setViewMode] = useState<ViewMode>(() => {
    const saved = localStorage.getItem("viewMode");
    return saved === "thumbnail" ? "thumbnail" : "list";
  });
  const [activeTab, setActiveTab] = useState<"user" | "shared">("user");
  const tabs: { key: TabKey; label: string }[] = [
    { key: "user", label: "Your Chatbots" },
    { key: "shared", label: "Shared Chatbots" },
  ];

  const setViewMode = (mode: ViewMode) => {
    _setViewMode(mode);
    localStorage.setItem("viewMode", mode);
  };

  /**
   * Sets a cookie to store the chatbot count for a given URL slug.
   *
   * @param urlSlug - The unique identifier for the chatbot group.
   * @param chatbotCount - The number of chatbots to store.
   * @param days - Number of days until the cookie expires.
   */
  const setCookie = (urlSlug: string, chatbotCount: number, days: number) => {
    const MS_PER_DAY = 24 * 60 * 60 * 1000;
    const expires = new Date(Date.now() + days * MS_PER_DAY).toUTCString();
    const cookieValue = `${urlSlug}_chatbot_count=${chatbotCount}; path=/; expires=${expires};`;
    try {
      document.cookie = cookieValue;
      console.debug(loggerPrefix, `setCookie(): ${cookieValue}`);
    } catch (e) {
      console.warn(loggerPrefix, "setCookie(): Unable to set chatbot count cookie", e);
    }
  };

  /**
   * Retrieves the chatbot count stored in a cookie for a given URL slug.
   *
   * @param urlSlug - The unique identifier for the chatbot group.
   * @returns The number of chatbots stored in the cookie, or undefined if not found or invalid.
   */
  const getCookie = (urlSlug: string): number | undefined => {
    const cookieName = `${urlSlug}_chatbot_count`;
    const cookies = document.cookie.split(";").map((c) => c.trim());
    for (const cookie of cookies) {
      if (cookie.startsWith(cookieName + "=")) {
        const strVal = cookie.substring(cookieName.length + 1);
        const numVal = parseInt(strVal, 10);
        const retVal = isNaN(numVal) ? undefined : numVal;
        console.debug(loggerPrefix, `getCookie(): Retrieved cookie for ${cookieName}:`, retVal);
        return retVal;
      }
    }
    console.warn(
      loggerPrefix,
      `getCookie(): Cookie for ${cookieName} not found. If you are not under /, it may not be visible due to cookie path restrictions.`,
    );
    return undefined;
  };

  /**
   * Loads chatbot data from the backend API and updates state.
   *
   * @param isMounted - Whether the component is still mounted (prevents state updates on unmounted components).
   * @param setterCallback - State setter for updating the chatbot list.
   * @param urlSlug - The API slug for the chatbot group (e.g., "owned" or "shared").
   * @param invalidateCache - If true, forces the backend to invalidate its cache (default: false).
   */
  const load = async (
    isMounted: boolean,
    setterCallback: React.Dispatch<React.SetStateAction<Chatbot[]>>,
    urlSlug: string,
    invalidateCache = false,
  ) => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      // Join base and slug manually to handle local path base
      let base = sessionContext.promptListApiUrl;
      if (!base.endsWith("/")) base += "/";
      let slug = urlSlug.startsWith("/") ? urlSlug.slice(1) : urlSlug;
      let url = base + slug;
      if (!url.endsWith("/")) url += "/";
      url += `?invalidate_cache=${invalidateCache}`;
      const response = await fetchDjangoUrl(
        JSON.stringify({}),
        url,
        sessionContext.djangoSessionCookieName,
        sessionContext.csrfCookieName,
        sessionContext.cookieDomain,
      );
      // sleep for 5 seconds to simulate loading state (for testing purposes)
      await new Promise((resolve) => setTimeout(resolve, 5000));

      if (!response.ok) {
        let errorMsg = `Failed to load chatbots (${response.status})`;
        try {
          const errorJson = await response.json();
          if (errorJson && errorJson.error) {
            errorMsg = errorJson.error;
          }
        } catch {
          console.error(loggerPrefix, "load(): Failed to load chatbots due to an unknown error.");
        }
        throw new Error(errorMsg);
      }

      const payload = (await response.json()) as ChatbotListApiResponse;

      setCookie(urlSlug, payload.chatbots.length, 7);

      if (isMounted) {
        setterCallback(payload.chatbots);
      }
    } catch (error) {
      if (isMounted) {
        console.error(loggerPrefix, "load(): Error loading chatbots:", error);
        setErrorMessage(error instanceof Error ? error.message : "Unable to load chatbots.");
      }
    } finally {
      if (isMounted) {
        setIsLoading(false);
      }
    }
  };

  const handleRequery = () => {
    load(true, setUserChatbots, "owned", true);
    load(true, setSharedChatbots, "shared", true);
  };

  const maxGhostRows = 25;
  const clamp = (val: number, min: number, max: number) => Math.max(min, Math.min(max, val));
  const userGhostCount = clamp(getCookie("owned") || 6, 0, maxGhostRows);
  const sharedGhostCount = clamp(getCookie("shared") || 6, 0, maxGhostRows);

  useEffect(() => {
    let isMounted = true;

    // See smarter.apps.prompt.views.listview.api.PromptListOwnershipFilter for expected values
    load(isMounted, setUserChatbots, "owned");
    load(isMounted, setSharedChatbots, "shared");

    return () => {
      isMounted = false;
    };
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
              isLoading={isLoading}
              ghostRows={userGhostCount}
              sessionContext={sessionContext}
              chatbots={userChatbots}
              onRequery={handleRequery}
            />
          ) : (
            <CardView sessionContext={sessionContext} chatbots={userChatbots} onRequery={handleRequery} />
          )
        ) : viewMode === "list" ? (
          <ListView
            isLoading={isLoading}
            ghostRows={sharedGhostCount}
            sessionContext={sessionContext}
            chatbots={sharedChatbots}
            onRequery={handleRequery}
          />
        ) : (
          <CardView sessionContext={sessionContext} chatbots={sharedChatbots} onRequery={handleRequery} />
        )}
      </div>
    </div>
  );
}

export default TabbedListView;
