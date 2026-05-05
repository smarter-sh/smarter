import type { Chatbot } from "@/lib/Types";

export const statusCell = (chatbot: Chatbot) => (
  <span className="prompt-list-status-icons">
    {chatbot.isAuthenticationRequired ? (
      <i
        className="fas fa-lock prompt-list-icon-lock"
        title="Authentication required"
        aria-label="Authentication required"
      />
    ) : (
      <i
        className="fas fa-unlock prompt-list-icon-unlock"
        title="No authentication required"
        aria-label="No authentication required"
      />
    )}
    {chatbot.deployed ? (
      <i
        className="fas fa-check prompt-list-icon-deployed"
        title="Deployed"
        aria-label="Deployed"
      />
    ) : null}
  </span>
);
