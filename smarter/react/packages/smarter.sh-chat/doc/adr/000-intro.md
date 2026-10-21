# ADR Introduction

Architectural Design Records (ADRs) are short documents that capture a single architectural or design decision, its context, and its consequences. Less is more: keep them brief.

These are the ADRs of Smarter Chat, `@smarter.sh/ui-chat`: the chat UI of Smarter LLMClients, an npm package of React components, which the Smarter web console's prompt engineering workbench imports too, and an embed script for any web page. They follow the Smarter platform's own [ADRs](https://github.com/smarter-sh/smarter/tree/main/docs/source/adr), especially [ADR-019: React](https://github.com/smarter-sh/smarter/blob/main/docs/source/adr/019-react.rst), and use the same layout as the ADRs of the [Python SDK](https://github.com/smarter-sh/smarter-python/tree/main/doc/adr) and of the platform integrations, such as [Smarter Chat for WordPress](https://github.com/smarter-sh/smarter-wordpress/tree/main/doc/adr). Where Smarter Chat applies one of the platform's decisions, its ADR says so.

The developer guide on docs.smarter.sh, [Developing Smarter Chat](https://docs.smarter.sh/smarter-framework/smarter-chat/development.html), explains how the code works. These records explain why it is built that way.

See: [Michael Nygard's ADRs](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions.html)

## Guidelines for writing ADRs

- **One decision per ADR.**
- **Be concise.** Focus on clarity and brevity.
- **State the context:** the forces that led to the decision.
- **List the alternatives**, and why they weren't chosen.
- **Explain the decision**, and **describe its consequences**, positive and negative.
- **Use simple language**, for future contributors without today's context.
- **Use the same format** as the others, and **reference related ADRs**.

## Index

- [ADR-001: Scope: the Chat UI of Smarter LLMClients](001-scope.md)
- [ADR-002: One Source, Three Builds](002-three-builds.md)
- [ADR-003: Its Own Repository, Inside the Platform's Workspace](003-repository.md)
- [ADR-004: The Api Contract Is Generated from the Platform](004-api-contract.md)
- [ADR-005: Configured by the LLMClient's Manifest](005-manifest-configuration.md)
- [ADR-006: The Embed Script](006-embed-script.md)
- [ADR-007: Distribution: npm and jsDelivr](007-distribution.md)
- [ADR-008: Security](008-security.md)
- [ADR-009: Chat Sessions and Browser Storage](009-sessions.md)
- [ADR-010: Bundle Size and Lazy Loading](010-bundle-size.md)
- [ADR-011: Accessibility](011-accessibility.md)
- [ADR-012: Testing](012-testing.md)
- [ADR-013: CI/CD and Releases](013-ci-cd.md)
- [ADR-014: Semantic Versioning and the Public Api](014-versioning.md)
- [ADR-015: Code Quality](015-code-quality.md)
- [ADR-016: Licensing](016-licensing.md)
- [ADR-017: Documentation](017-documentation.md)
- [ADR-018: Translations](018-translations.md)
- [ADR-019: The Workbench Hosts the Chat](019-hosted-by-the-workbench.md)
- [ADR-020: Part of the Platform's Repository](020-part-of-the-platform-repository.md)
