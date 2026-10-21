# ADR-007: Distribution: npm and jsDelivr

## Status

Accepted

## Context

React applications install packages from npm. Pages without a bundler need a url for `embed.js`. Hosting a CDN of our own would be one more service to run, and the integrations need a version they can pin and test.

## Decision

- The package is published to **npm** as `@smarter.sh/ui-chat`, by `release.yml`, with npm's trusted publishing (OIDC) and a provenance statement: no npm token is stored (ADR-013).
- `embed.js` is served by **jsDelivr** from npm: `https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@<range>/dist/embed.js`. `package.json`'s `jsdelivr` and `unpkg` fields name it, and its `exports` include `./embed`.
- **Only releases from `main` are published**, with the `latest` dist-tag. Prereleases from `alpha` and `beta` are GitHub releases and tags only: `release.yml` skips them, and fails for a tag that isn't on `main`. So an alpha never reaches npm, jsDelivr or a website.
- After each release, `release.yml` asks jsDelivr to purge the major and minor ranges, so that sites on `@0` see it in minutes.
- **The integrations pin an exact version**, which they have tested: WordPress (`SMARTER_CHAT_EMBED_VERSION`, and a copy in the plugin), Drupal (`EmbedConfig::EMBED_VERSION`), Shopify (`smarter-chat-script-url.liquid`), the docs site generators (`embed.json`). Google Tag Manager's template uses a minor range. Hand-written tags are documented with `@0`, with advice to pin.
- `embed.js` and `embed/` are always copied together when a site hosts them itself.

## Alternatives Considered

- **Our own CDN** (e.g. `cdn.smarter.sh`). One more service, bucket and invalidation to run, for what jsDelivr does from npm.
- **Prereleases on npm with an `alpha` or `beta` dist-tag.** They would be on jsDelivr too, under an exact version, and a release run for an alpha branch could publish by accident. Integrations test against a packed tarball or a build of `main` instead.
- **Integrations on a floating range.** An embed release could break a site that the integration's tests never saw.

## Consequences

- **Positive:**
  - A release is on npm and the CDN within minutes, with no infrastructure of our own.
  - Every integration's release names the embed version that it was tested with.
- **Negative:**
  - A release that isn't on npm is a 404 for every site that embeds it, so publishing is part of CI, not a manual step.
  - A new embed release reaches pinned integrations only when each one bumps its pin (their `monthly-maintenance` skills).

## Related ADRs

- [ADR-006: The Embed Script](006-embed-script.md)
- [ADR-013: CI/CD and Releases](013-ci-cd.md)
- [ADR-014: Semantic Versioning and the Public Api](014-versioning.md)
