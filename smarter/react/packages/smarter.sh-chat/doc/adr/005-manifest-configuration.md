# ADR-005: Configured by the LLMClient's Manifest

## Status

Accepted

## Context

A chat on a website has two kinds of settings: what the chatbot is (its model, prompt, name, welcome message, examples, logo and colors), and where it sits on a page (its size, its corner, whether it starts open). Website owners redeploy their sites rarely, and often can't; a chatbot's owner changes its manifest often. The same LLMClient may be embedded on many sites, and in the workbench.

## Decision

- **The manifest decides what the chat is and how it looks.** The configuration api returns the LLMClient's public `spec.config.prompt` settings and its `spec.config.styles`, and the chat applies them. There is no prop for the welcome message, the model or a color.
- **The page decides where the chat is.** Props (`SmarterChatProps`), and the embed script's options (ADR-006), are only about placement, size, sessions, authentication and developer features. Only `apiUrl` (`chatbot` in the embed script) is required.
- **Styles become css custom properties** on the chat's root `.SmarterChat` element, e.g. `--smarter-chat-header-bg` (`src/lib/styles.ts`), which `styles.css` applies to chatscope's components with chatscope's own values as fallbacks. A setting that is left out changes nothing. chatscope's theme is compiled from scss, so its colors can't be changed at run time any other way.
- **Values are validated again in the browser**, though the platform validated them, because a page may embed a chat from any platform: a value that isn't a plain css value, an `https` image url, or a plain Google font name is ignored (ADR-008).
- Class names are prefixed `smarter-chat-`, so that a page's own css can override what the manifest doesn't cover.

## Alternatives Considered

- **Props for the chatbot's text and colors.** Every embedding site would need a redeploy for a manifest change, and copies would disagree.
- **A theme object in javascript.** It can't be set from a manifest, or by the embed script's users, who write no javascript.
- **Rebuilding chatscope's scss per LLMClient.** Not possible at run time.

## Consequences

- **Positive:**
  - Applying a manifest changes the chat everywhere, at the next new session.
  - The embed script needs no styling options beyond the launcher's.
- **Negative:**
  - A visual feature needs a platform change first: a field in the styles model, then the contract (ADR-004), then the css variable here.

## Related ADRs

- [ADR-001: Scope: the Chat UI of Smarter LLMClients](001-scope.md)
- [ADR-004: The Api Contract Is Generated from the Platform](004-api-contract.md)
- [ADR-008: Security](008-security.md)
