# ADR-014: Semantic Versioning and the Public Api

## Status

Accepted

Follows the platform's [ADR-020: Semantic Versioning](https://github.com/smarter-sh/smarter/blob/main/docs/source/adr/020-semantic-versioning.rst).

## Context

semantic-release versions the package from conventional commit messages (ADR-013). A version number is only meaningful if "breaking" has a definition, and this package has more public surface than its TypeScript exports.

## Decision

Versions follow [semver](https://semver.org): `feat` is a minor release, `fix` and `perf` are patches, and a `BREAKING CHANGE:` footer is a major release. `docs`, `test`, `style`, `refactor`, `chore` and `ci` release nothing. `alpha` and `beta` publish prereleases (`0.10.0-alpha.1`).

The **public api**, whose incompatible change is breaking, is:

- the exports of `src/index.ts`, including the enums (`MenuItems`: adding a tab is a feature, removing one is breaking),
- `SmarterChatProps`, their names, types and defaults,
- the stylesheet paths (`dist/ui-chat.css`, `style.css`) and `package.json`'s `exports`,
- the embed script's options, in all three spellings, `<smarter-chat>`, its parts (`::part(...)`), its `smarter-chat-toggle` event, `window.SmarterChat` and `window.SmarterChatConfig`,
- the names of the cookies and `localStorage` keys (ADR-009), which sites' privacy notices list,
- the `smarter-chat-` class names and `--smarter-chat-*` css properties that pages override,
- the oldest version of the api contract that it reads (ADR-004).

The contract with the platform is versioned separately (`chat-contract-v2`). A new package version keeps working with older platforms; when a feature needs a newer platform, its release notes say so.

While the version is 0.x, a breaking change is still announced with `BREAKING CHANGE:`, and avoided where a deprecation will do (e.g. `ChatbotConfig`, a deprecated alias of `LLMClientConfig`, and `chatbot`, a non-enumerable alias of `llmclient` in the configuration).

## Alternatives Considered

- **Versioning the embed script separately.** It is built from the same source, and the integrations pin one version of the package.

## Consequences

- **Positive:**
  - Sites on `@0` and integrations that bump their pin can trust a minor release.
- **Negative:**
  - Renaming an option or a class name is breaking, so names are chosen carefully the first time.

## Related ADRs

- [ADR-004: The Api Contract Is Generated from the Platform](004-api-contract.md)
- [ADR-007: Distribution: npm and jsDelivr](007-distribution.md)
- [ADR-013: CI/CD and Releases](013-ci-cd.md)
