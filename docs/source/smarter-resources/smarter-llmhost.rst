Smarter MCP Client
=====================

Overview
--------

The Smarter LLMHost app provides a standardized interface for deploying and
managing self-hosted large language models within Smarter-orchestrated applications.
Rather than routing every inference request through a third-party model provider,
LLMHost lets an organization register its own model deployments — whether
served from a Hugging Face checkpoint via vLLM, a quantized GGUF model through
Ollama, or a custom inference stack — as first-class, managed resources.
This allows prompts and engineering loops to target self-hosted models with
the same consistency as any hosted provider, while Smarter remains responsible
for endpoint configuration, credential resolution, health monitoring, and
cost tracking. By separating model deployment from application logic, LLMHost
enables new models to be brought online, swapped, or retired without modifying
the surrounding AI application.

LLMHost operates as a managed registry and health-tracking layer between Smarter
and the underlying inference infrastructure. During initialization it captures
a deployment's provenance (its source repository and revision), its capabilities
(context window, quantization, supported modalities), and its serving
configuration (inference engine, API format, endpoint), then makes that deployment
available for controlled invocation by prompts, agents, and workflows. Each
configured host is continuously monitored through Smarter's health-check
infrastructure, and its authentication credentials are resolved through Smarter's
Secret store rather than persisted as plaintext, ensuring that self-hosted
capabilities remain subject to the same governance and operational controls as
any other Smarter resource. This architecture allows organizations to run open,
freely downloadable models alongside commercial providers while maintaining centralized
configuration, observability, and cost visibility across all AI-assisted interactions.

The Smarter LLMHost app is included in v0.15.0 and later. It enables Account administrators
to register and manage self-hosted model deployments through the Smarter administration
interface, eliminating the need to hard-code inference endpoints or distribute
deployment details across individual applications.

.. seealso::

    - :doc:`Smarter Installation Guide <../smarter-platform/installation>`
    - :doc:`OpenAI Getting Started Guide <../smarter-framework/guides/openai-api-getting-started-guide>`

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   llmhost/api
   llmhost/const
   llmhost/management
   llmhost/manifest
   llmhost/models
   llmhost/serializers
   llmhost/signals
   llmhost/tasks
   llmhost/views
