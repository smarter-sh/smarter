# ADR-004: The Api Contract Is Generated from the Platform

## Status

Accepted

## Context

The chat makes two POST requests to a Smarter platform: `<apiUrl>config/`, for the LLMClient's public configuration and the session's history, and the LLMClient's prompt api, for each prompt, optionally streamed as Server-Sent Events. Installed copies of the chat, on other people's websites and pinned to old versions, talk to platforms of every version. Hand-written TypeScript types and hand-written fixtures drifted from what the platform actually sent.

## Decision

The platform owns the contract, as Pydantic models in `smarter.apps.prompt.contract.models`:

1. The platform's `make chat-contract` exports them as a JSON Schema, and copies it into this repository's `contract/chat-contract.schema.json`.
2. `npm run contract:types` (`scripts/contract-types.mjs`) generates `src/contract.gen.ts` from it, exported as the `Contract` namespace. `src/types.ts` aliases those types; nothing redefines them.
3. `src/contract.test.ts` fails if `src/contract.gen.ts` is out of date, and validates every fixture in `src/mocks/fixtures.ts` against the schema with Ajv, so a test can't pass against a response the platform never sends.

The contract is **versioned**. The chat asks for version 2 with `X-Smarter-Capabilities: chat-contract-v2`, and still reads version 1 from older platforms, which ignore the header; `normalizeConfig()` converts it. A breaking change is a new version, asked for with a new capability, never a change to an existing one. `src/lib/api.ts` is the only module that calls `fetch`.

## Alternatives Considered

- **Types written by hand in this repository.** That is what drifted.
- **OpenAPI and a generated client.** The chat's two endpoints, with their event stream, don't need a client; the types and the fixture checks are what was missing. The platform's OpenAPI document (`smarter.apps.api.v1.contract`) also describes the two endpoints (`/api/v1/llm-clients/{id}/config/` and `prompt/`), with the chat contract's schemas as their bodies, but the chat contract's own JSON Schema is the narrower, versioned source the chat's types are generated from. The Smarter SDKs and cli pin a copy of the OpenAPI document instead, because they call many of its routes (their ADR-022).
- **Breaking changes in place, with the package and the platform released together.** Embedded copies are pinned and cached on sites that nobody updates.

## Consequences

- **Positive:**
  - A change to the platform's models reaches the chat's types, and a test fails on whichever side is out of date.
  - A new package works with older platforms.
- **Negative:**
  - `contract/` and `src/contract.gen.ts` are never edited here; a field is added on the platform first (see the `smarter-chat-development` skill).
  - Fields that some platforms don't send yet must be optional, and read with a fallback.

## Related ADRs

- [ADR-001: Scope: the Chat UI of Smarter LLMClients](001-scope.md)
- [ADR-012: Testing](012-testing.md)
- [ADR-014: Semantic Versioning and the Public Api](014-versioning.md)
