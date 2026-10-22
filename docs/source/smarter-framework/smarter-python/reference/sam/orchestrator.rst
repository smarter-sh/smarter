..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMOrchestrator
===============

``smarter.models.sam.orchestrator``
-----------------------------------

.. py:module:: smarter.models.sam.orchestrator

SAM model of the ``Orchestrator`` kind, generated from the Smarter platform's JSON Schema.

Do not edit: run ``scripts/generate_sam_models.py``. See :mod:`smarter.models.sam`.

.. py:class:: HarnessRole

   Bases: :class:`enum.Enum`

   Role an LLMClient (Harness) plays within an Orchestrator.

   Values must stay aligned with
   smarter.apps.orchestrator.models.OrchestratorHarness.Role.


.. py:class:: OrchestrationStrategy

   Bases: :class:`enum.Enum`

   Coordination pattern the Orchestrator applies across its member LLMClients.

   Values must stay aligned with
   smarter.apps.orchestrator.models.OrchestrationStrategy.


.. py:class:: SAMDependency

   Bases: :class:`smarter.models.sam.base.SAMModel`

   A resource that depends on the resource that a manifest describes.

   .. py:attribute:: kind
      :type: str

      Kind[String]: The SAM kind of the resource that depends on this resource, e.g. LLMClient.

      Read only.


   .. py:attribute:: name
      :type: str

      Name[String]: The name of the resource that depends on this resource.

      Read only.



.. py:class:: SAMOrchestratorHarnessConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   A single LLMClient (Harness) membership within the Orchestrator.

   Mirrors smarter.apps.orchestrator.models.OrchestratorHarness. The
   llmClientName is a reference by name, not by primary key — resolved
   against the account's existing LLMClients at apply time.

   .. py:attribute:: config
      :type: dict[str, Any] | None

      Per-membership overrides (e.g. temperature, system prompt fragment, tool allowlist).


   .. py:attribute:: executionOrder
      :type: Optional

      Relative ordering for sequential/supervisor strategies.


   .. py:attribute:: isActive
      :type: bool | None


   .. py:attribute:: llmClientName
      :type: str

      Name of an existing LLMClient to attach as a Harness.


   .. py:attribute:: role
      :type: smarter.models.sam.orchestrator.HarnessRole | None



.. py:class:: SAMOrchestratorMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Orchestrator Manifest - Metadata class.

   .. py:attribute:: annotations
      :type: None | list[dict[str, str | int | float | bool | datetime.date | datetime.datetime | uuid.UUID | bytes | list | dict[str, Any]]]

      The manifest annotations.

      Used for storing arbitrary metadata as
                  key-value pairs. Example: [{'smarter.sh/test-manifest/project-name': 'Scooby dooby do'}]. The
                  key should be a valid url-friendly string. The value accepts
                  multi-line string values (YAML block scalars) and various scalar types including
                  str, int, float, bool, datetime.date, datetime.datetime, decimal.Decimal, uuid.UUID, bytes, list, dict.


   .. py:attribute:: description
      :type: str | None

      The description for this resource.

      Be brief. Keep it under 255 characters.


   .. py:attribute:: name
      :type: str

      The camelCase name of the manifest resource.


   .. py:attribute:: tags
      :type: list[str] | None

      The tags of the manifest.

      Used for generic resource categorization and search. Example: ['tag1', 'tag2']


   .. py:attribute:: version
      :type: str | None

      The semantic version of the manifest.

      Example: 0.1.0



.. py:class:: SAMOrchestratorSpecConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Spec block for an Orchestrator SAM manifest.

   Mirrors smarter.apps.orchestrator.models.Orchestrator. Consumed by the
   manifest controller to create/update the corresponding Orchestrator
   model instance and its OrchestratorHarness memberships.

   .. py:attribute:: harnesses
      :type: list

      LLMClients (Harnesses) that participate in this Orchestrator.


   .. py:attribute:: isActive
      :type: bool | None


   .. py:attribute:: maxIterations
      :type: Optional

      Upper bound on orchestration loop iterations.


   .. py:attribute:: strategy
      :type: smarter.models.sam.orchestrator.OrchestrationStrategy | None



.. py:class:: SAMOrchestratorStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Orchestrator Manifest - Status class.

   .. py:attribute:: accountNumber
      :type: str

      Orchestrator.status.account_number: The account owner of this Orchestrator.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.orchestrator.SAMDependency] | None

      Dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop referring to it, before it can be deleted.

      Lists only the resources that you can read. Read only.


   .. py:attribute:: modified
      :type: datetime

      The date in which this resource was most recently changed.

      Read only.


   .. py:attribute:: recordLocator
      :type: str

      RecordLocator[String]: An optional identifier used to locate the resource record associated with this manifest.

      Read only.


   .. py:attribute:: username
      :type: str

      Orchestrator.status.username: The Smarter user who created this Orchestrator.

      Read only.



.. py:class:: SAMOrchestratorSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Orchestrator Manifest Orchestrator.spec.

   .. py:attribute:: config
      :type: SAMOrchestratorSpecConfig

      Orchestrator.spec.config[object].

      The configuration for the Orchestrator.



.. py:class:: SAMOrchestrator

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - Orchestrator.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMOrchestratorMetadata

      Orchestrator.metadata[obj]: Required, the Orchestrator metadata.


   .. py:attribute:: spec
      :type: SAMOrchestratorSpec

      Orchestrator.spec[obj]: Required, the Orchestrator specification.


   .. py:attribute:: status
      :type: smarter.models.sam.orchestrator.SAMOrchestratorStatus | None

      Orchestrator.status[obj]: Optional, Read-only.

      Stateful status information about the Orchestrator.
