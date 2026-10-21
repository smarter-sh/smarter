# ADR-016: Licensing

## Status

Accepted

## Context

Smarter is open source under the GNU Affero General Public License. Smarter Chat is part of its web console, and is also distributed on its own, to run on other people's websites.

## Decision

Smarter Chat is licensed **AGPL-3.0-or-later**, as Smarter is (`LICENSE`, and `license` in `package.json`). Its dependencies must have licenses compatible with it; React, chatscope, DOMPurify, marked, highlight.js, KaTeX and Mermaid have permissive ones. The embed script and the library bundle some of those dependencies, so a new dependency's license is checked before it is added.

## Alternatives Considered

- **A permissive license for the chat alone.** That is a decision for the copyright holder, and would make the web console's code available under two licenses.

## Consequences

- **Positive:**
  - One license across the Smarter project.
- **Negative:**
  - Some organizations restrict AGPL dependencies; the embed script, loaded from a CDN, is the usual answer for them, but that is their counsel's call, not ours.

## Related ADRs

- [ADR-007: Distribution: npm and jsDelivr](007-distribution.md)
