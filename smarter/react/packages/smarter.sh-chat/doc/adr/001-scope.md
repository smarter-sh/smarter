# ADR-001: Scope: the Chat UI of Smarter LLMClients

## Status

Accepted

Amended by [ADR-019](019-hosted-by-the-workbench.md): the developer Console is the platform's workbench's, which hosts the chat.

## Context

A Smarter chatbot is an LLMClient: a YAML manifest, applied to a Smarter platform, which runs the LLM, its Plugins, Functions, Guardrails and MCP servers, and keeps the chat sessions. The platform needs a chat window for its prompt engineering workbench, and its users need the same chat on their own websites, many of which aren't built with React.

General-purpose chat UIs exist, but they talk to an LLM provider directly, or to a backend that the website's owner writes. Neither displays what Smarter adds: the LLMClient's configuration and styles, the progress of tool and Plugin calls, sandbox mode and the developer Console.

## Decision

Smarter Chat is the front end of a deployed Smarter LLMClient, and of nothing else. It has one required input, the LLMClient's url, and it talks only to that LLMClient's two endpoints (its configuration and its prompt api, ADR-004). It:

- renders the chat thread, markdown, code, math and diagrams, and the progress of a running prompt,
- applies the LLMClient's configuration and styles (ADR-005),
- optionally shows sandbox mode, and lets a page that hosts it, such as the workbench, follow it and add to it (ADR-019),
- ships as an npm package, which the workbench imports, and an embed script, from one source (ADR-002).

It never calls an LLM provider, never holds a provider's api key, and doesn't manage LLMClients. Building, styling, securing and deploying the chatbot happen on the Smarter platform, with its manifest.

## Alternatives Considered

- **A general-purpose chat component, with adapters for other backends.** Every feature would need a lowest common denominator, and the contract with Smarter (ADR-004) couldn't be generated and tested end to end.
- **A separate chat for websites and for the workbench.** Two chats would drift apart, and the workbench would stop showing what visitors see.

## Consequences

- **Positive:**
  - A change to a manifest changes the chat on every website that embeds it, without a redeploy.
  - The workbench, the npm package, the embed script and the five platform integrations show the same chat.
- **Negative:**
  - The package is useless without a Smarter platform.
  - Sandbox mode ships in the package too, behind a prop that is off by default (`toggleMetadata`). The developer Console is the workbench's own (ADR-019).

## Related ADRs

- [ADR-002: One Source, Three Builds](002-three-builds.md)
- [ADR-019: The Workbench Hosts the Chat](019-hosted-by-the-workbench.md)
- [ADR-004: The Api Contract Is Generated from the Platform](004-api-contract.md)
- [ADR-005: Configured by the LLMClient's Manifest](005-manifest-configuration.md)
