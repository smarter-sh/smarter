// ----------------------------------------------------------------------------
// Prompt List Component.
// ----------------------------------------------------------------------------
import { useEffect, useMemo, useState } from "react";
import "./styles.css";
import fetchDjangoUrl from "../../lib/django";

type Chatbot = {
  id: number;
  name: string;
  version: string | null;
  createdAt: string;
  updatedAt: string;
  provider: string;
  defaultModel: string | null;
  defaultTemperature: number | null;
  defaultMaxTokens: number | null;
  defaultSystemRole: string | null;
  description: string | null;
  dnsVerificationStatus: string | null;
  appAssistant: string | null;
  appName: string | null;
  appLogoUrl: string | null;
  deployed: boolean;
  isAuthenticationRequired?: boolean;
  tags: string[];
  urlChatbot: string | null;
  userProfile: {
    user: {
      username: string;
      email: string;
    };
  };
  urls: {
    manifest: string;
    chat: string;
    config: string;
  };
};

type PromptListApiResponse = {
  chatbots: {
    user: Chatbot[];
    shared: Chatbot[];
  };
};

type ViewMode = "list" | "thumbnail";

interface PromptListProps {
  myResourcesApiUrl: string;
  csrfCookieName: string;
  csrftoken: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
}

function PromptList({ myResourcesApiUrl, csrfCookieName, csrftoken, djangoSessionCookieName, cookieDomain }: PromptListProps) {
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
          myResourcesApiUrl,
          csrftoken,
          djangoSessionCookieName,
          csrfCookieName,
          cookieDomain,
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
          setErrorMessage(error instanceof Error ? error.message : "Unable to load chatbots.");
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
  }, [myResourcesApiUrl, csrftoken, djangoSessionCookieName, csrfCookieName, cookieDomain]);

  const userChatbots = useMemo(() => apiData?.chatbots.user ?? [], [apiData]);
  const sharedChatbots = useMemo(() => apiData?.chatbots.shared ?? [], [apiData]);

  const formatDateTime = (value: string | null | undefined) => {
    if (!value) {
      return "-";
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString(undefined, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const pluginsText = (chatbot: Chatbot) => {
    if (!chatbot.tags || chatbot.tags.length === 0) {
      return "-";
    }
    return chatbot.tags.join(", ");
  };

  const statusCell = (chatbot: Chatbot) => (
    <span className="prompt-list-status-icons">
      {chatbot.isAuthenticationRequired ? (
        <i className="fas fa-lock prompt-list-icon-lock" title="Authentication required" aria-label="Authentication required" />
      ) : (
        <i className="fas fa-unlock prompt-list-icon-unlock" title="No authentication required" aria-label="No authentication required" />
      )}
      {chatbot.deployed ? <i className="fas fa-check prompt-list-icon-deployed" title="Deployed" aria-label="Deployed" /> : null}
    </span>
  );

  const renderListViewTable = (title: string, chatbots: Chatbot[], cardClassName: string) => (
    <div className={cardClassName}>
      <div className="prompt-list-heading-wrap">
        <h3 className="text-center">{title}</h3>
      </div>
      <div className="table-responsive prompt-list-table-wrap">
        <table className="table table-striped table-hover align-middle">
          <thead className="table-light">
            <tr>
              <th className="p-3">Name</th>
              <th className="width-100">Created</th>
              <th className="width-100">Updated</th>
              <th>Provider</th>
              <th className="min-width-150">Model</th>
              <th>Plugins</th>
              <th>Status</th>
              <th />
              <th />
            </tr>
          </thead>
          <tbody>
            {chatbots.map((chatbot) => (
              <tr key={chatbot.id}>
                <td className="name-col p-3">
                  <a href={chatbot.urls.chat}>
                    {chatbot.name}
                    {chatbot.version ? ` v${chatbot.version}` : ""}
                  </a>
                </td>
                <td className="width-100">{formatDateTime(chatbot.createdAt)}</td>
                <td className="width-100">{formatDateTime(chatbot.updatedAt)}</td>
                <td>
                  {chatbot.appLogoUrl ? (
                    <img
                      src={chatbot.appLogoUrl}
                      alt={`${chatbot.provider} logo`}
                      className="provider-logo d-none"
                    />
                  ) : null}
                  {chatbot.provider}
                </td>
                <td className="min-width-150">{chatbot.defaultModel || "default"}</td>
                <td>{pluginsText(chatbot)}</td>
                <td>{statusCell(chatbot)}</td>
                <td>
                  <a href={chatbot.urls.chat} className="btn btn-sm btn-primary">Open</a>
                </td>
                <td className="p-3">
                  <a href={chatbot.urls.manifest} className="btn btn-sm btn-info">Manifest</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderDetailRow = (label: string, value: string | number | null | undefined) => {
    if (value === null || value === undefined || value === "") {
      return null;
    }

    return (
      <tr>
        <td className="prompt-list-detail-label">{label}</td>
        <td className="prompt-list-detail-value">{value}</td>
      </tr>
    );
  };

  const renderThumbnailCards = (title: string, chatbots: Chatbot[], cardClassName: string) => (
    <div className={cardClassName}>
      <div className="prompt-list-heading-wrap">
        <h3 className="text-center">{title}</h3>
      </div>
      {chatbots.map((chatbot) => (
        <article className="col-12 mt-1 p-2" key={chatbot.id}>
          <div className={`card card-flush h-xl-100 chatbot-card ${title === "Your Chatbots" ? "user-chatbot-card" : "smarter-chatbot-card"}`}>
            <div className="p-5 prompt-list-card-header">
              <span className="prompt-list-header-icons">
                {chatbot.isAuthenticationRequired ? (
                  <i className="fas fa-lock prompt-list-icon-lock" aria-label="Authentication required" />
                ) : (
                  <i className="fas fa-unlock prompt-list-icon-unlock" aria-label="No authentication required" />
                )}
                {chatbot.deployed ? <i className="fas fa-check prompt-list-icon-deployed" aria-label="Deployed" /> : null}
              </span>
              <h4 className="card-title card-label fw-bold text-gray-800 text-center prompt-list-card-title">
                <a href={chatbot.urls.chat} className="prompt-list-card-link">
                  {chatbot.name}
                  {chatbot.version ? ` v${chatbot.version}` : ""}
                </a>
              </h4>
            </div>
            <div className="card-body py-2">
              <table className="prompt-list-details-table">
                <tbody>
                  {renderDetailRow("Owner", chatbot.userProfile?.user?.username)}
                  {renderDetailRow("Created", formatDateTime(chatbot.createdAt))}
                  {renderDetailRow("Last updated", formatDateTime(chatbot.updatedAt))}
                  {renderDetailRow("URL", chatbot.urlChatbot || chatbot.urls.chat)}
                  {renderDetailRow("Provider", chatbot.provider)}
                  {renderDetailRow("Model", chatbot.defaultModel)}
                  {renderDetailRow("Temperature", chatbot.defaultTemperature)}
                  {renderDetailRow("Max Tokens", chatbot.defaultMaxTokens)}
                  {renderDetailRow("System Role", chatbot.defaultSystemRole)}
                  {renderDetailRow("Description", chatbot.description)}
                  {renderDetailRow("DNS status", chatbot.dnsVerificationStatus)}
                  {renderDetailRow("App assistant", chatbot.appAssistant)}
                  {renderDetailRow("App name", chatbot.appName)}
                  {renderDetailRow("Plugins", pluginsText(chatbot))}
                </tbody>
              </table>
              <div className="prompt-list-card-actions">
                <a href={chatbot.urls.chat} className="btn btn-sm btn-primary">Open</a>
                <a href={chatbot.urls.manifest} className="btn btn-sm btn-info">Manifest</a>
              </div>
            </div>
          </div>
        </article>
      ))}
    </div>
  );

  if (isLoading) {
    return <div className="prompt-list-feedback">Loading chatbots...</div>;
  }

  if (errorMessage) {
    return <div className="alert alert-danger">{errorMessage}</div>;
  }

  return (
    <section id="chatbots">
      <div id="toggle-buttons" className="mb-4">
        <div className="btn-group border border-light rounded-3 bg-white" role="group" aria-label="View toggle">
          <button
            type="button"
            className={`btn btn-sm ${viewMode === "list" ? "btn-outline-primary active" : "btn-outline-secondary"}`}
            title="List View"
            aria-label="List View"
            onClick={() => setViewMode("list")}
          >
            <i className="fas fa-list" />
          </button>
          <button
            type="button"
            className={`btn btn-sm ${viewMode === "thumbnail" ? "btn-outline-primary active" : "btn-outline-secondary"}`}
            title="Thumbnail View"
            aria-label="Thumbnail View"
            onClick={() => setViewMode("thumbnail")}
          >
            <i className="fas fa-th-large" />
          </button>
        </div>
      </div>

      <div className={viewMode === "list" ? "list-view" : "card-view"}>
        {userChatbots.length > 0 ? renderListViewTable("Your Chatbots", userChatbots, "mt-15") : null}
        {renderListViewTable("Shared Chatbots", sharedChatbots, userChatbots.length > 0 ? "mt-5" : "mt-15")}
      </div>

      <div className={viewMode === "thumbnail" ? "card-view" : "list-view"}>
        <section className="row g-5 g-xl-10 mb-l-10">
          {userChatbots.length > 0 ? renderThumbnailCards("Your Chatbots", userChatbots, "mt-15") : null}
          {renderThumbnailCards("Shared Chatbots", sharedChatbots, userChatbots.length > 0 ? "mt-5" : "mt-15")}
        </section>
      </div>
    </section>
  );
}

export default PromptList;
