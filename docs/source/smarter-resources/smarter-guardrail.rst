Smarter Guardrail
=====================

Overview
--------

The Smarter Guardrail app is responsible for enforcing constraints on the interaction
between an application and a large language model. Rather than relying solely
on prompt instructions such as "do not reveal sensitive information" or
"respond only in JSON," guardrails validate inputs, outputs, and execution
state before information is accepted or returned. They may sanitize user input,
reject prompt injection attempts, enforce schema validation, filter unsafe or
out-of-scope responses, verify citations, limit tool access, or require
structured output that conforms to predefined contracts. Guardrails operate as
deterministic software controls surrounding the probabilistic behavior of the model,
ensuring that business rules and security requirements are enforced independently
of the LLM's reasoning.

Smarter Guardrail enforces these constraints in three layers:

 - **Pre-execution guardrails** inspect user requests for malicious content, policy violations, or malformed data before the prompt reaches the model.
 - **Runtime guardrails** constrain the model's available tools, memory, and permissions, preventing unauthorized actions or excessive autonomy during execution.
 - **Post-execution guardrails** validate the generated response against expected formats, confidence thresholds, or organizational policies before returning it to the caller.

Together, these layers transform an LLM from a general-purpose text generator into a predictable application component whose behavior can be monitored, audited, and controlled, making it suitable for production environments where reliability, compliance, and security are essential.


.. note::

  The Smarter Guardrail app is included in v0.15.0 and later. It shifts management of LLM guardrail
  API credentials from an IT and DevOps responsibility to the Account administrators.

.. seealso::

    - :doc:`Smarter Installation Guide <../smarter-platform/installation>`
    - :doc:`OpenAI Getting Started Guide <../smarter-framework/guides/openai-api-getting-started-guide>`

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   guardrail/api
   guardrail/const
   guardrail/management
   guardrail/manifest
   guardrail/models
   guardrail/serializers
   guardrail/signals
   guardrail/tasks
   guardrail/views
