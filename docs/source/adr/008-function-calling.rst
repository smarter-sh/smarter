ADR-008: Function Calling
=========================

Status
------
Accepted

Context
-------
The core mission of the Smarter platform is to provide no-code abstractions through manifests, the CLI, and the broker model, while also enabling extensibility for LLM function calling. The `Smarter Plugin` class is central to this mission, serving as the primary mechanism for extending and integrating function calling capabilities.

Decision
--------
The platform will use the `Smarter Plugin` class to enable extensible LLM function calling, supporting the no-code approach via manifests and the broker model.

Alternatives Considered
-----------------------
- Implementing function calling without a plugin-based architecture.
- Relying solely on built-in functions without extensibility.

Consequences
------------
- **Positive:**
  - Promotes extensibility and flexibility for LLM function calling.
  - Maintains a no-code approach for users through manifests and CLI.
  - Centralizes integration logic in the `Smarter Plugin` class.
- **Negative:**
  - Requires contributors to understand and use the plugin architecture.
  - May introduce complexity in plugin management and compatibility.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
- [ADR-005: Manifests](005-manifests)
- [ADR-024: Broker Model](024-broker-model)
