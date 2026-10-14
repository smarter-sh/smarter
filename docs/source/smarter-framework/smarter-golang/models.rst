Models
======

Every response of the SDK is decoded into a struct, never into a ``map[string]any``. A struct's
fields have Go names, and JSON tags of the API's own names, so it encodes back to the platform's
JSON. An unknown field never fails a decode, so the SDK keeps working when the platform adds fields
to a response. An optional number or boolean is a pointer (``smarter.Deref`` reads one, and
``smarter.Ptr`` makes one), and a timestamp is an ISO 8601 string.

SAM structs
-----------

The ``sam`` package has a struct of every :doc:`manifest <../smarter-manifests>` kind, e.g.
``sam.LLMClient``, ``sam.Guardrail`` and ``sam.Secret``, and the structs of their parts.
``sam.Kinds`` maps each kind to a function that returns a new struct of the kind.

.. code-block:: go

   described, err := client.LLMClients.Describe(ctx, "customer_support")
   if err != nil {
       return err
   }
   llmclient, err := smarter.ToSAM[sam.LLMClient](described)
   if err != nil {
       return err
   }
   fmt.Println(llmclient.Spec.Config.Prompt.Provider, llmclient.Spec.Config.Prompt.DefaultModel)

The platform's own manifest models depend on Django, so the SDK can't import them. Its structs are
generated from the JSON Schema that the platform publishes for each kind, which is the same schema
that ``client.Manifests.JSONSchema(ctx, kind)`` returns, and the tests check that every kind's
example manifest decodes into its struct, without a field that the struct doesn't declare. The
structs check a manifest's structure. The platform's models also apply business rules that a JSON
Schema can't express, so validate a manifest with ``client.Manifests.Validate`` before you rely on
it.

API contracts
-------------

The platform publishes the contracts of its APIs as Pydantic models, and the SDK mirrors them:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - SDK structs
     - Platform contract
   * - ``PromptChatAPI...``
     - The :doc:`Smarter Chat API contract <../smarter-chat/api-contract>`, version 2: an LLMClient's
       configuration (``PromptChatAPIConfig``), the prompt API's request and response, and the
       prompt's progress events.
   * - ``SAMJournalAPI...``, ``JournalEntry``, ``JournalPage``
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

The other structs model the REST API's resources, e.g. ``smarter.LLMClient``, ``smarter.Guardrail``
and ``smarter.Vectorstore``. Each embeds ``smarter.Resource``, the fields that every resource shares,
whose ``Ref()`` is the resource's ``smarter.ID``.
