Models
======

Every response of the SDK is validated with a `Zod <https://zod.dev>`__ schema, and its TypeScript
type is inferred from that schema, so the two can't disagree. A model is exported as a schema and a
type of the same name, e.g. ``Guardrail``: the schema validates, and the type annotates.

.. code-block:: typescript

   import { Guardrail } from "smarter-api";

   const guardrail: Guardrail = Guardrail.parse(JSON.parse(text));

Every schema keeps fields that it doesn't declare, so that the SDK keeps working when the platform
adds fields to a response. A model's fields are the API's own names, exactly as the API returns
them, camelCase for the REST resources (``hashedId``) and snake_case for the chat contract
(``session_key``), so ``JSON.stringify()`` of a response is the platform's JSON. Timestamps are ISO
8601 strings.

SAM types
---------

The SDK has a TypeScript type of every :doc:`manifest <../smarter-manifests>` kind, e.g.
``SAMLLMClient``, ``SAMGuardrail`` and ``SAMSecret``. ``SAMKinds`` maps each kind to its type, and
``SAM_KINDS`` lists the kinds.

.. code-block:: typescript

   import { SAM_KINDS } from "smarter-api";

   const llmclient = (await client.llmClients.describe("customer_support")).toSam("LLMClient");
   console.log(llmclient.spec.config.prompt.provider, llmclient.spec.config.prompt.defaultModel, llmclient.status?.deployed);
   console.log(SAM_KINDS);

The platform's own manifest models depend on Django, so the SDK can't import them. Its types are
generated from the JSON Schema that the platform publishes for each kind, which is the same schema
that ``client.manifests.jsonSchema(kind)`` returns, and ``toSam()`` validates a manifest against that
schema with Ajv. The tests check that every kind's example manifest validates. The schemas check a
manifest's structure. The platform's models also apply business rules that a JSON Schema can't
express, so validate a manifest with ``client.manifests.validate()`` before you rely on it.

API contracts
-------------

The platform publishes the contracts of its APIs as Pydantic models, and the SDK mirrors them as Zod
schemas, with the platform's model names:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - SDK schemas
     - Platform contract
   * - ``PromptChatApi...``
     - The :doc:`Smarter Chat API contract <../smarter-chat/api-contract>`, version 2: an LLMClient's
       configuration (``PromptChatApiConfig``), the prompt API's request and response, and the
       prompt's progress events.
   * - ``SAMJournalApi...``, ``JournalEntry``, ``JournalPage``
     - The :doc:`Smarter Journal <../smarter-api/smarter-journal>` contract: the envelope of every
       journaled response, its error body, and a journal entry.
   * - ``ViteManifest``, ``ReactAppAssets``
     - The :doc:`Django-React integration <../developer-reference/react-integration>` contract: a
       React app's Vite manifest, and the assets that a template includes, for tools that build React
       apps for a Smarter platform.

The SDK's tests compare the chat and journal mirrors with the platform's committed JSON Schemas
and examples, and fail when the platform adds a field that the SDK doesn't declare yet.

REST models
-----------

The other schemas model the REST API's resources, e.g. ``LLMClient``, ``Guardrail`` and
``Vectorstore``.
