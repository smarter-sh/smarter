# ADR-009: Chat Sessions and Browser Storage

## Status

Accepted

## Context

A visitor's conversation should survive a page reload and, on a website, follow them from page to page. In the workbench, each LLMClient needs its own session. Two chatbots on one website must not share one. The chat runs on other people's sites, which must be able to describe what it stores.

## Decision

- **The platform stores the conversation.** The browser holds only the session's key, in a cookie, which the configuration request sends; a new session's key comes back in the configuration and is saved. The configuration returns the session's history, which restores the thread.
- **Cookies are first-party, `SameSite=Lax`, with an expiry of one day by default.** The session cookie is for the page's path by default (so each workbench page has its own session), or for `cookiePath`.
- **The embed script's session cookie is per chatbot host, for the whole site**: `smarter_chat_<chatbot host>`, path `/`, so a conversation follows the visitor across the site, and two chatbots keep separate sessions. Its debug cookie is the same name with `_debug`.
- **`SmarterChat` holds its state in plain `useState`.** There is no store; the platform is the source of truth.

The list of cookies and keys is documented in "What the Component Stores in the Browser", on docs.smarter.sh, which the integrations' privacy texts copy. Changing a name is a breaking change for them.

## Alternatives Considered

- **The conversation in `localStorage`.** It would duplicate the platform's history, and a shared computer would keep it after the session ends.
- **A third-party cookie on the platform's domain.** Browsers block them.
- **One session cookie name for every chatbot.** Two chatbots on one site would overwrite each other's session.

## Consequences

- **Positive:**
  - A reload or a new page continues the conversation, and a page that hosts the chat, such as the workbench, can show the session's history.
- **Negative:**
  - The session cookie needs a mention in a site's cookie notice.
  - A browser that blocks first-party cookies starts a new chat on every page load.

## Related ADRs

- [ADR-006: The Embed Script](006-embed-script.md)
- [ADR-008: Security](008-security.md)
