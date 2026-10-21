# ADR-008: Security

## Status

Accepted

Follows the platform's [ADR-016: Security](https://github.com/smarter-sh/smarter/blob/main/docs/source/adr/016-security.rst).

## Context

The chat displays text from an LLM, from tools, and from users, any of which can be steered by an attacker (prompt injection). It runs inside other people's web pages, with their cookies, and is configured by values that a page or a platform supplies. chatscope's `Message` takes html strings, not React elements.

## Decision

- **Messages are rendered by one pipeline** (`src/lib/messages.ts`): user messages are escaped, with only markdown links and images converted; every other role is GitHub flavored markdown, rendered by `marked` with renderers that display raw html as text, and the result is **sanitized with DOMPurify** before it is displayed. Every string that reaches a `Message` comes from `messageFactory()`. A new markdown feature may allow exactly the tags and attributes it emits in `sanitize()`, never more.
- **Urls are restricted**: links and images are `http(s)` or relative; inline images are raster `data:` urls only (`png`, `jpeg`, `gif`, `webp`), never svg. Links open in a new tab with `rel="noopener noreferrer"`.
- **Mermaid's svg is sanitized again** (`sanitizeSvg()`), because a diagram's source comes from the LLM.
- **Every configuration value is validated in the browser**: css values, image urls and Google font names in `styles.ts`, and every embed option in `options.ts` (the chatbot url must be `http(s)`, sizes and colors plain css values, cookie names and paths a safe pattern). An invalid value is dropped, not escaped.
- **The api key is public.** An `apiKey` prop, or `api-key` option, is sent as `Authorization: Token <apiKey>`, and anyone who can view the page can read it. The docs say to create a key per page; LLMClients without a key are public, and charged to their owner.
- **The chat calls only its LLMClient's host**, with `credentials: "include"`, which the LLMClient's `allowedOrigins` (CORS) permits. A new request header must be added to the platform's `CORS_ALLOW_HEADERS`.
- **`console.debug` is stripped from production builds** (`manualPureFunctions` in `vite.config.ts`), so debug logging can't leak configuration.

## Alternatives Considered

- **Rendering markdown to React elements** (e.g. `react-markdown`). chatscope's message component takes html, and the Copy and Code buttons are wired by delegation.
- **Escaping configuration values instead of dropping invalid ones.** An escaped css value can still break out of its declaration; a pattern that allows only plain values can't.
- **Hiding the api key behind a proxy.** It would put each website's server in the path of every prompt, and break streaming (ADR-001).

## Consequences

- **Positive:**
  - Html from any source passes through one sanitizer.
- **Negative:**
  - Legitimate html in a response is displayed as text.
  - Pages that need a private chatbot must rely on the platform's own authentication, not on the key.

## Related ADRs

- [ADR-005: Configured by the LLMClient's Manifest](005-manifest-configuration.md)
- [ADR-006: The Embed Script](006-embed-script.md)
- [ADR-009: Chat Sessions and Browser Storage](009-sessions.md)
