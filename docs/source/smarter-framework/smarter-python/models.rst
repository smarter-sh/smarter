Models
======

Every request and response of the SDK is a Pydantic model, as the platform's own API is
(:doc:`ADR-031 <../../adr/031-pydantic-over-json>`). The SDK's models are in :mod:`smarter.models`.

Every model keeps fields that it doesn't declare, so that the SDK keeps working when the platform
adds fields to a response. ``to_dict()`` and ``to_json()`` return a model with the API's own field
names, and a model's extra fields are in ``model_extra``.

SAM models
----------

:mod:`smarter.models.sam` has a typed model of every :doc:`manifest <../smarter-manifests>` kind,
e.g. ``SAMLLMClient``, ``SAMGuardrail`` and ``SAMSecret``. ``SAM_MODELS`` maps each kind to its model.

.. code-block:: python

   from smarter.models.sam import SAM_MODELS, SAMLLMClient

   llmclient: SAMLLMClient = client.llm_clients.describe("customer_support").to_sam()
   print(llmclient.spec.config.prompt.provider, llmclient.spec.config.prompt.defaultModel, llmclient.status.deployed)
   print(sorted(SAM_MODELS))

The platform's own manifest models depend on Django, so the SDK can't import them. Its models are
generated from the JSON Schema that the platform publishes for each kind, which is the same schema
that ``client.manifests.json_schema(kind)`` returns, and the tests check that every kind's example
manifest parses. The generated models check a manifest's structure. The platform's models also
apply business rules that a JSON Schema can't express, so validate a manifest with
``client.manifests.validate()`` before you rely on it.

API contracts
-------------

The platform publishes the contracts of its APIs as Pydantic models, and the SDK mirrors them:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - SDK module
     - Platform contract
   * - :mod:`smarter.models.chat`
     - The :doc:`Smarter Chat API contract <../smarter-chat/api-contract>`, version 2: an LLMClient's
       configuration (``PromptChatApiConfig``), the prompt API's request and response, and the
       prompt's progress events.
   * - :mod:`smarter.models.journal`
     - The :doc:`Smarter Journal <../smarter-api/smarter-journal>` contract: the envelope of every
       journaled response, its error body, and a journal entry.
   * - :mod:`smarter.models.react`
     - The :doc:`Django-React integration <../developer-reference/react-integration>` contract: a
       React app's Vite manifest, and the assets that a template includes, for tools that build React
       apps for a Smarter platform.

The SDK's tests compare the chat and journal mirrors with the platform's committed JSON Schemas
and examples, and fail when the platform adds a field that the SDK doesn't declare yet.

REST models
-----------

The other modules model the REST API's resources, e.g. :class:`~smarter.models.llmclient.LLMClient`,
:class:`~smarter.models.guardrail.Guardrail` and :class:`~smarter.models.vectorstore.Vectorstore`.
Their attributes are snake_case, and they read the API's camelCase fields.
