// ----------------------------------------------------------------------------
// Prompt List Component.
// ----------------------------------------------------------------------------
import { useEffect, useMemo, useState } from "react";

import fetchDjangoUrl from "@/lib/django";
import CombinedListViews from "@/components/CombinedListViews/Component";
import CombinedCardViews from "@/components/CombinedCardViews/Component";
import type { PromptListApiResponse, ViewMode, SessionContext } from "@/lib/Types";

import "./styles.css";

interface ViewToggleButtonProps {
  viewMode: ViewMode;
  onClick: () => void;
}

function ListViewToggleButton({ viewMode, onClick }: ViewToggleButtonProps) {
  return (
    <button
      type="button"
      className={`btn btn-sm ${viewMode === "list" ? "btn-outline-primary active" : "btn-outline-secondary"}`}
      title="List View"
      aria-label="List View"
      onClick={onClick}
    >
      <i className="fas fa-list" />
    </button>
  );
}

function ThumbnailViewToggleButton({viewMode, onClick}: ViewToggleButtonProps) {
  return (
    <button
      type="button"
      className={`btn btn-sm ${viewMode === "thumbnail" ? "btn-outline-primary active" : "btn-outline-secondary"}`}
      title="Thumbnail View"
      aria-label="Thumbnail View"
      onClick={onClick}
    >
      <i className="fas fa-th-large" />
    </button>
  );
}

function ToggleButton({ viewMode, setViewMode }: { viewMode: ViewMode; setViewMode: (mode: ViewMode) => void }) {
  return (
      <div id="toggle-buttons" className="mb-4">
        <div
          className="btn-group border border-light rounded-3 bg-white"
          role="group"
          aria-label="View toggle"
        >
          <ListViewToggleButton
            viewMode={viewMode}
            onClick={() => setViewMode("list")}
          />
          <ThumbnailViewToggleButton
            viewMode={viewMode}
            onClick={() => setViewMode("thumbnail")}
          />
        </div>
      </div>
  );
}

interface PromptsProps {
  sessionContext: SessionContext;
}

function Prompts({sessionContext}: PromptsProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [apiData, setApiData] = useState<PromptListApiResponse | null>(null);

  useEffect(() => {
    let isMounted = true;

    const load = async () => {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const response = await fetchDjangoUrl(
          JSON.stringify({}),
          sessionContext.myResourcesApiUrl,
          sessionContext.csrftoken,
          sessionContext.djangoSessionCookieName,
          sessionContext.csrfCookieName,
          sessionContext.cookieDomain,
        );

        if (!response.ok) {
          throw new Error(`Failed to load chatbots (${response.status})`);
        }

        const payload = (await response.json()) as PromptListApiResponse;
        if (isMounted) {
          setApiData(payload);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(
            error instanceof Error ? error.message : "Unable to load chatbots.",
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    load();

    return () => {
      isMounted = false;
    };
  }, [sessionContext]);

  const chatbots = useMemo(
    () => apiData?.chatbots ?? { user: [], shared: [] },
    [apiData],
  );

  if (isLoading) {
    return <div className="prompt-list-feedback">Loading chatbots...</div>;
  }

  if (errorMessage) {
    return <div className="alert alert-danger">{errorMessage}</div>;
  }

  return (

    <>
      <ToggleButton viewMode={viewMode} setViewMode={setViewMode} />

      {viewMode === "list" ? (
        <CombinedListViews sessionContext={sessionContext} chatbots={chatbots} />
      ) : (
        <CombinedCardViews sessionContext={sessionContext} chatbots={chatbots} />
      )}
    </>
  );
}

export default Prompts;
