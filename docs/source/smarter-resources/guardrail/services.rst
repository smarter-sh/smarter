Services
========

The guardrail services evaluate an LLMClient's Guardrails on a prompt. The
:class:`~smarter.apps.guardrail.services.pipeline.GuardrailPipeline` runs each Guardrail with the
:class:`~smarter.apps.guardrail.services.engine.GuardrailEngine`, which extracts the text of the
stage, evaluates the Guardrail's strategy, applies its action, and records a GuardrailEvent.

.. toctree::
   :maxdepth: 1

   services/pipeline
   services/engine
   services/text-extraction
   services/actions
   services/events
   services/strategies
