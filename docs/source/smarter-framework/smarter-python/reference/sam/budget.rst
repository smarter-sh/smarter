..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMBudget
=========

``smarter.models.sam.budget``
-----------------------------

.. py:module:: smarter.models.sam.budget

SAM model of the ``Budget`` kind, generated from the Smarter platform's JSON Schema.

Do not edit: run ``scripts/generate_sam_models.py``. See :mod:`smarter.models.sam`.

.. py:class:: SAMBudgetMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Budget Manifest - Metadata class.

   .. py:attribute:: annotations
      :type: None | list[dict[str, Union[str, int, float, bool, datetime.date, datetime.datetime, Annotated[str, StringConstraints(strip_whitespace=None, to_upper=None, to_lower=None, strict=None, min_length=None, max_length=None, pattern='^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$')], uuid.UUID, bytes, list, dict[str, Any]]]]

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



.. py:class:: Action

   Bases: :class:`enum.Enum`

   Budget.spec.config.action: block further charges when a limit is reached, or only warn.


.. py:class:: Period

   Bases: :class:`enum.Enum`

   Budget.spec.config.period: the billing period of periodicLimit and duration.


.. py:class:: Unit

   Bases: :class:`enum.Enum`

   Budget.spec.config.unit: what the limits measure: cost in USD, or total tokens.


.. py:class:: SAMBudgetSpecConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Budget Manifest Budget.spec.config: the budget's limits.

   .. py:attribute:: absoluteLimit
      :type: Union

      Budget.spec.config.absoluteLimit: the most that may be spent in total, from when the budget is attached.

      0 means no limit.


   .. py:attribute:: action
      :type: smarter.models.sam.budget.Action | None

      Budget.spec.config.action: block further charges when a limit is reached, or only warn.


   .. py:attribute:: duration
      :type: Optional

      Budget.spec.config.duration: the billing periods, from when the budget is attached, after which it no longer applies.

      0 means never.


   .. py:attribute:: message
      :type: Optional

      Budget.spec.config.message: what people are told when the budget blocks their request.

      Defaults to a description of the limit that was reached.


   .. py:attribute:: period
      :type: smarter.models.sam.budget.Period | None

      Budget.spec.config.period: the billing period of periodicLimit and duration.


   .. py:attribute:: periodicLimit
      :type: Union

      Budget.spec.config.periodicLimit: the most that may be spent in a billing period.

      0 means no limit.


   .. py:attribute:: unit
      :type: smarter.models.sam.budget.Unit | None

      Budget.spec.config.unit: what the limits measure: cost in USD, or total tokens.


   .. py:attribute:: warningThreshold
      :type: Optional

      Budget.spec.config.warningThreshold: the percentage of a limit at which a warning is sent.

      0 means never.



.. py:class:: Kind

   Bases: :class:`enum.Enum`

   Budget.spec.resources.kind: the resource's manifest kind, e.g. LLMClient.


.. py:class:: SAMBudgetSpecResource

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Budget Manifest Budget.spec.resources[]: a resource that the budget is enforced on.

   Either kind and name, with an optional accountNumber, or a recordLocator.

   .. py:attribute:: accountNumber
      :type: str | None

      Budget.spec.resources.accountNumber: the account that the resource belongs to.

      Defaults to your own.


   .. py:attribute:: kind
      :type: smarter.models.sam.budget.Kind | None

      Budget.spec.resources.kind: the resource's manifest kind, e.g. LLMClient.


   .. py:attribute:: name
      :type: str | None

      Budget.spec.resources.name: the resource's name.

      For an Account, its account number; for a User, the username.


   .. py:attribute:: recordLocator
      :type: str | None

      Budget.spec.resources.recordLocator: any resource's record locator, e.g. llmclient-rc2x, in place of kind and name.



.. py:class:: SAMBudgetStatusResource

   Bases: :class:`smarter.models.sam.base.SAMModel`

   The budget versus the actual spending of one of the budget's resources.

   Read only.

   .. py:attribute:: absoluteActual
      :type: Union

      Budget.status.resources.absoluteActual: spending since startDate.


   .. py:attribute:: absolutePercent
      :type: float | None

      Budget.status.resources.absolutePercent: absoluteActual, as a percentage of the limit.


   .. py:attribute:: expiresAt
      :type: datetime.datetime | None

      Budget.status.resources.expiresAt: when the budget's duration ends.


   .. py:attribute:: isActive
      :type: bool

      Budget.status.resources.isActive: whether the budget is enforced on it.


   .. py:attribute:: isLocked
      :type: bool

      Budget.status.resources.isLocked: whether the budget refuses further charges.


   .. py:attribute:: lockReason
      :type: str | None

      Budget.status.resources.lockReason: which limit was reached.


   .. py:attribute:: periodicActual
      :type: Union

      Budget.status.resources.periodicActual: spending this billing period.


   .. py:attribute:: periodicPercent
      :type: float | None

      Budget.status.resources.periodicPercent: periodicActual, as a percentage of the limit.


   .. py:attribute:: recordLocator
      :type: str

      Budget.status.resources.recordLocator: the resource's record locator.


   .. py:attribute:: startDate
      :type: datetime

      Budget.status.resources.startDate: when the budget was attached.



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



.. py:class:: SAMBudgetSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Budget Manifest Budget.spec.

   .. py:attribute:: config
      :type: SAMBudgetSpecConfig

      Budget.spec.config[object].

      The limits of the Budget.


   .. py:attribute:: resources
      :type: list[smarter.models.sam.budget.SAMBudgetSpecResource] | None

      Budget.spec.resources[list].

      The resources that the Budget is enforced on. Resources that are removed from the list are detached.



.. py:class:: SAMBudgetStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Budget Manifest - Status class.

   Read only.

   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.budget.SAMDependency] | None

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


   .. py:attribute:: resources
      :type: list[smarter.models.sam.budget.SAMBudgetStatusResource] | None

      Budget.status.resources: the budget versus the actual spending of each resource.

      Read only.



.. py:class:: SAMBudget

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - Budget.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMBudgetMetadata

      Budget.metadata[obj]: Required, the Budget metadata.


   .. py:attribute:: spec
      :type: SAMBudgetSpec

      Budget.spec[obj]: Required, the Budget specification.


   .. py:attribute:: status
      :type: smarter.models.sam.budget.SAMBudgetStatus | None

      Budget.status[obj]: Optional, Read-only.

      Stateful status information about the Budget.
