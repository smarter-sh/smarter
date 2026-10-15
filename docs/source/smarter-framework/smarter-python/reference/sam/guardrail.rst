..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMGuardrail
============

``smarter.models.sam.guardrail``
--------------------------------

.. py:module:: smarter.models.sam.guardrail

SAM model of the ``Guardrail`` kind, generated from the Smarter platform's JSON Schema.

Do not edit: run ``scripts/generate_sam_models.py``. See :mod:`smarter.models.sam`.

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



.. py:class:: SAMGuardrailMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Guardrail Manifest - Metadata class.

   .. py:attribute:: annotations
      :type: None | list[dict[str, Union[str, int, float, bool, datetime.date, datetime.datetime, Annotated[str, StringConstraints(strip_whitespace=None, to_upper=None, to_lower=None, strict=None, min_length=None, max_length=None, pattern='^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$', ascii_only=None)], uuid.UUID, bytes, list, dict[str, Any]]]]

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

   Guardrail.spec.config.action[str]: what the guardrail does when it triggers.

   One of: ['log', 'flag', 'redact', 'transform', 'block', 'escalate'].


.. py:class:: Category

   Bases: :class:`enum.Enum`

   Guardrail.spec.config.category[str]: the risk the guardrail addresses.

   One of: ['pii', 'secrets', 'prompt_injection', 'jailbreak', 'toxicity', 'self_harm', 'hallucination', 'off_topic', 'compliance', 'formatting', 'custom'].


.. py:class:: Mode

   Bases: :class:`enum.Enum`

   Guardrail.spec.config.mode[str]: enforce, to take the action, or monitor, to only record what the action would have been.


.. py:class:: Stage

   Bases: :class:`enum.Enum`

   Guardrail.spec.config.stage[str]: when the guardrail runs.

   One of: ['input', 'output', 'both'].


.. py:class:: Strategy

   Bases: :class:`enum.Enum`

   Guardrail.spec.config.strategy[str]: how the guardrail detects.

   One of: ['regex', 'keyword', 'detector', 'semantic', 'moderation', 'llm_judge'].


.. py:class:: SAMGuardrailSpecConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Guardrail Manifest Guardrail.spec.config.

   .. py:attribute:: action
      :type: Action

      Guardrail.spec.config.action[str]: what the guardrail does when it triggers.

      One of: ['log', 'flag', 'redact', 'transform', 'block', 'escalate'].


   .. py:attribute:: caseSensitive
      :type: bool | None

      Guardrail.spec.config.caseSensitive[bool]: whether the keyword strategy is case sensitive.


   .. py:attribute:: categories
      :type: list[str] | None

      Guardrail.spec.config.categories[list]: the moderation strategy's categories.

      Empty means all. Any of: ['harassment', 'harassment/threatening', 'hate', 'hate/threatening', 'illicit', 'illicit/violent', 'self-harm', 'self-harm/intent', 'self-harm/instructions', 'sexual', 'sexual/minors', 'violence', 'violence/graphic'].


   .. py:attribute:: category
      :type: smarter.models.sam.guardrail.Category | None

      Guardrail.spec.config.category[str]: the risk the guardrail addresses.

      One of: ['pii', 'secrets', 'prompt_injection', 'jailbreak', 'toxicity', 'self_harm', 'hallucination', 'off_topic', 'compliance', 'formatting', 'custom'].


   .. py:attribute:: detectors
      :type: list[str] | None

      Guardrail.spec.config.detectors[list]: the detector strategy's detectors.

      Any of: ['credit_card', 'us_ssn', 'email', 'phone_number', 'ip_address', 'iban', 'aws_access_key', 'private_key', 'api_key', 'jwt', 'password_assignment'].


   .. py:attribute:: failClosed
      :type: bool | None

      Guardrail.spec.config.failClosed[bool]: if true, block when the check itself fails, e.g. because the LLM provider is unavailable.

      If false, the failure is recorded, and the prompt continues.


   .. py:attribute:: flags
      :type: list[str] | None

      Guardrail.spec.config.flags[list]: the regex strategy's flags.

      Any of: ['IGNORECASE', 'MULTILINE', 'DOTALL'].


   .. py:attribute:: isActive
      :type: bool | None

      Guardrail.spec.config.isActive[bool]: whether the guardrail runs.


   .. py:attribute:: judgePrompt
      :type: str | None

      Guardrail.spec.config.judgePrompt[str]: the llm_judge strategy's prompt, with a {text} placeholder for the text to judge.

      Any other braces must be doubled, e.g. {{ and }}.


   .. py:attribute:: keywords
      :type: list[str] | None

      Guardrail.spec.config.keywords[list]: the keyword strategy's words and phrases.


   .. py:attribute:: message
      :type: str | None

      Guardrail.spec.config.message[str]: what block returns to the user, instead of the LLM's reply.


   .. py:attribute:: mode
      :type: smarter.models.sam.guardrail.Mode | None

      Guardrail.spec.config.mode[str]: enforce, to take the action, or monitor, to only record what the action would have been.


   .. py:attribute:: model
      :type: str | None

      Guardrail.spec.config.model[str]: the model of the semantic, moderation and llm_judge strategies.


   .. py:attribute:: pattern
      :type: str | None

      Guardrail.spec.config.pattern[str]: the regex strategy's regular expression.


   .. py:attribute:: priority
      :type: Optional

      Guardrail.spec.config.priority[int]: the order in which guardrails run.

      Lower runs first.


   .. py:attribute:: provider
      :type: str | None

      Guardrail.spec.config.provider[str]: the name of the Smarter LLM Provider that the semantic, moderation and llm_judge strategies call.

      Defaults to openai.


   .. py:attribute:: referenceTexts
      :type: list[str] | None

      Guardrail.spec.config.referenceTexts[list]: the semantic strategy's examples of what to detect.


   .. py:attribute:: replacement
      :type: str | None

      Guardrail.spec.config.replacement[str]: what redact and transform replace each match with.

      Defaults to [REDACTED], which an empty replacement also means. {label} is replaced with what matched, e.g. credit_card. For the regex strategy, transform may refer to groups, e.g. .


   .. py:attribute:: severity
      :type: Optional

      Guardrail.spec.config.severity[int]: from 1 (low) to 5 (critical), for reporting and review.


   .. py:attribute:: stage
      :type: Stage

      Guardrail.spec.config.stage[str]: when the guardrail runs.

      One of: ['input', 'output', 'both'].


   .. py:attribute:: strategy
      :type: Strategy

      Guardrail.spec.config.strategy[str]: how the guardrail detects.

      One of: ['regex', 'keyword', 'detector', 'semantic', 'moderation', 'llm_judge'].


   .. py:attribute:: threshold
      :type: Optional

      Guardrail.spec.config.threshold[float]: the minimum confidence, from 0 to 1, at which the semantic, moderation and llm_judge strategies trigger.

      Defaults to 0.8.


   .. py:attribute:: wholeWord
      :type: bool | None

      Guardrail.spec.config.wholeWord[bool]: whether the keyword strategy matches whole words only.



.. py:class:: SAMGuardrailStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Guardrail Manifest - Status class.

   Read only. Besides ownership, it reports the guardrail's events of the last 30 days. The
   LLMClients that use it are reported in ``dependencies``.

   .. py:attribute:: accountNumber
      :type: str

      Guardrail.status.account_number: The account owner of this Guardrail.

      Read only.


   .. py:attribute:: blocked
      :type: int | None

      Guardrail.status.blocked: how many prompts this Guardrail blocked in the last 30 days.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.guardrail.SAMDependency] | None

      Dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop referring to it, before it can be deleted.

      Lists only the resources that you can read. Read only.


   .. py:attribute:: errors
      :type: int | None

      Guardrail.status.errors: how many times this Guardrail failed to run in the last 30 days.

      Read only.


   .. py:attribute:: lastTriggered
      :type: datetime.datetime | None

      Guardrail.status.lastTriggered: when this Guardrail last triggered.

      Read only.


   .. py:attribute:: modified
      :type: datetime

      The date in which this resource was most recently changed.

      Read only.


   .. py:attribute:: recordLocator
      :type: str

      RecordLocator[String]: An optional identifier used to locate the resource record associated with this manifest.

      Read only.


   .. py:attribute:: triggered
      :type: int | None

      Guardrail.status.triggered: how many times this Guardrail triggered in the last 30 days.

      Read only.


   .. py:attribute:: username
      :type: str

      Guardrail.status.username: The Smarter user who created this Guardrail.

      Read only.



.. py:class:: SAMGuardrailSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Guardrail Manifest Guardrail.spec.

   .. py:attribute:: config
      :type: SAMGuardrailSpecConfig

      Guardrail.spec.config[object].

      The configuration for the Guardrail.



.. py:class:: SAMGuardrail

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - Guardrail.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMGuardrailMetadata

      Guardrail.metadata[obj]: Required, the Guardrail metadata.


   .. py:attribute:: spec
      :type: SAMGuardrailSpec

      Guardrail.spec[obj]: Required, the Guardrail specification.


   .. py:attribute:: status
      :type: smarter.models.sam.guardrail.SAMGuardrailStatus | None

      Guardrail.status[obj]: Optional, Read-only.

      Stateful status information about the Guardrail.
