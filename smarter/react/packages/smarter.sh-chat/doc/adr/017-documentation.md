# ADR-017: Documentation

## Status

Accepted

Follows the platform's documentation conventions: docs.smarter.sh is evergreen, and is the complete guide.

## Context

The package's readers are website owners who embed a chat, React developers who install the package, platform developers who change the chat, and the developers of the integrations. npm displays the README of the published version only.

## Decision

- **`README.md`** is the npm page: what the chat is, installation, the React quick start, the embed script and its options, the props, the TypeScript exports and the api contract in brief, with links to docs.smarter.sh for everything else. It changes on npmjs.com only with the next release.
- **docs.smarter.sh** (`docs/source/smarter-framework/smarter-chat*` in the platform's repository) is the complete guide: features, embedding, the api contract, how the web console hosts it, and the developer guide. Docs are evergreen: a new feature is woven into the existing pages, never a "what's new" section.
- **`.github/CONTRIBUTING.md`** is the workflow: `make` targets, working inside the platform's workspace, commits and releases.
- **`doc/adr/`** (these records) say why; **`skills/`** tell coding agents how.
- Code is documented where it is: a module comment that says what the module is for and where it fits, and doc comments on exported functions, props and options. They are TypeScript doc comments, which editors show.
- A change to an option, a prop, a cookie or a contract field updates the README's tables and the docs pages in the same change, in each repository.

## Alternatives Considered

- **A docs site for the package alone.** It would duplicate docs.smarter.sh, where the LLMClient, its manifest and its styles are documented.

## Consequences

- **Positive:**
  - One complete guide, beside the documentation of the LLMClients that the chat displays.
- **Negative:**
  - A user-facing change usually needs a commit in the platform's repository too, for its docs.

## Related ADRs

- [ADR-003: Its Own Repository, Inside the Platform's Workspace](003-repository.md)
- [ADR-014: Semantic Versioning and the Public Api](014-versioning.md)
