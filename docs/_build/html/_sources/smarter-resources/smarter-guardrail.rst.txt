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

A Smarter **Guardrail** is a manifest-declared control that inspects the text passing between a
user and an LLM, and acts on what it finds. Each Guardrail runs on one or both **stages** of a prompt:

 - **Input guardrails** inspect the user's latest message before it reaches the LLM, or the
   LLMClient's plugins, MCP clients and functions. They redact PII and secrets, and block prompt
   injection, jailbreaks, abuse and off-topic requests.
 - **Output guardrails** inspect the LLM's reply before it is returned to the user. They redact
   leaked PII and secrets, withhold unsafe or non-compliant content, and repair formatting.

Guardrails are deterministic software controls around the probabilistic behavior of the model, so
that business rules and security requirements are enforced independently of the LLM's reasoning,
and every intervention is recorded for audit.

.. note::

  **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's Claude
  Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will be documented.
  The Smarter Guardrail app is included in v0.15.0 and later.

.. seealso::

    - :doc:`Smarter Installation Guide <../smarter-platform/installation>`
    - :doc:`OpenAI Getting Started Guide <../smarter-framework/guides/openai-api-getting-started-guide>`

How It Works
------------

A Guardrail is a Smarter resource, defined by a YAML manifest, and managed with the ``smarter`` CLI:

.. code-block:: console

    smarter apply -f pii-redaction.yaml
    smarter describe guardrail pii_redaction
    smarter get guardrails
    smarter delete guardrail pii_redaction

An LLMClient uses Guardrails by listing them, by name, in its manifest's ``spec.guardrails``,
alongside ``spec.plugins`` and ``spec.functions``. A name resolves to the user's own Guardrail
first, and otherwise to a Guardrail shared with them, such as a built-in one.

.. code-block:: yaml

    apiVersion: smarter.sh/v1
    kind: LLMClient
    metadata:
      name: support_assistant
    spec:
      config:
        provider: openai
        defaultModel: gpt-4o-mini
      guardrails:
        - pii_redaction_input
        - prompt_injection_keyword_input
        - moderation_output
        - secrets_leak_output

On each prompt, the LLMClient's active Guardrails for the stage run **sequentially**, in
ascending order of ``priority``. Each Guardrail sees the text as changed by those before it, so
a redaction at priority 10 hides the redacted text from a Guardrail at priority 20. The first
Guardrail that **blocks** stops the pipeline:

 - A blocked **input** is never sent to the LLM. The user receives the Guardrail's ``message``,
   as a reply whose ``finish_reason`` is ``content_filter``, and the blocked message is replaced
   in the conversation's history, so that it is not sent to the LLM on a later prompt.
 - A blocked **output** is replaced with the Guardrail's ``message``.

Each Guardrail that triggers records a **GuardrailEvent**: the Guardrail, LLMClient, session,
stage, disposition, confidence and a masked excerpt of the matched text. Events are visible in the
Django admin, where they can be marked reviewed, and through the Guardrail api. Old events are
purged daily, except flagged and escalated events that await review.

The Manifest
------------

.. code-block:: yaml

    apiVersion: smarter.sh/v1
    kind: Guardrail
    metadata:
      name: pii_redaction
      description: Redact credit card numbers and email addresses.
      version: 1.0.0
    spec:
      config:
        stage: both                       # input | output | both
        category: pii                     # what the Guardrail protects against
        strategy: detector                # how it finds it
        detectors: [credit_card, email]
        action: redact                    # what it does when it finds it
        replacement: "[REDACTED {label}]"
        severity: 4                       # 1 (lowest) to 5 (highest)
        mode: enforce                     # enforce | monitor
        failClosed: false
        priority: 10
        isActive: true

**Categories** classify a Guardrail, for reporting: ``pii``, ``secrets``, ``prompt_injection``,
``jailbreak``, ``toxicity``, ``self_harm``, ``hallucination``, ``off_topic``, ``compliance``,
``formatting`` and ``custom``.

Strategies
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 35 50

   * - Strategy
     - Fields
     - Behavior
   * - ``regex``
     - ``pattern``, ``flags`` (``IGNORECASE``, the default, ``MULTILINE``, ``DOTALL``)
     - Matches a regular expression. Locates its matches, so it can redact and transform.
   * - ``keyword``
     - ``keywords``, ``caseSensitive``, ``wholeWord``
     - Matches any of a list of words or phrases, tolerant of extra whitespace. Locating.
   * - ``detector``
     - ``detectors``
     - Built-in, validated detectors: ``credit_card`` (Luhn), ``us_ssn``, ``email``,
       ``phone_number``, ``ip_address``, ``iban`` (mod-97), ``aws_access_key``, ``private_key``,
       ``api_key``, ``jwt`` and ``password_assignment``. Locating.
   * - ``semantic``
     - ``referenceTexts``, ``threshold``, ``model``, ``provider``
     - Compares the text's embedding with those of the reference texts. Triggers when the
       cosine similarity reaches ``threshold``.
   * - ``moderation``
     - ``categories``, ``threshold``, ``model``, ``provider``
     - Scores the text with the provider's moderation model. Triggers when a category's score
       reaches ``threshold``, or the model flags it.
   * - ``llm_judge``
     - ``judgePrompt``, ``threshold``, ``model``, ``provider``
     - Asks an LLM for a JSON verdict ``{"triggered", "confidence", "rationale"}``. The prompt
       must contain ``{text}``, where the text is inserted. A system message tells the judge that
       the text is untrusted data, whose instructions it must not follow.

``regex``, ``keyword`` and ``detector`` run locally, in microseconds. ``semantic``, ``moderation``
and ``llm_judge`` call the ``provider`` (default ``openai``), with its API key, and add latency to
each prompt, so order them after the local Guardrails.

Actions
~~~~~~~

 - ``log``: record an event, and do nothing else.
 - ``flag``: record an event for review. The text is unchanged.
 - ``redact``: replace each match with ``replacement``. ``{label}`` in the replacement is the
   detector's name. Requires a locating strategy.
 - ``transform``: rewrite each regex match with ``replacement``, which may use back references such
   as ``\1``. Requires a locating strategy.
 - ``block``: stop the pipeline, and answer with ``message``.
 - ``escalate``: flag the event for human review, with its severity, and send the
   ``guardrail_escalated`` signal. The text is unchanged.

Modes and Failure
~~~~~~~~~~~~~~~~~

 - ``mode: monitor`` evaluates the Guardrail and records what it would have done, as a
   ``monitored`` event, without changing or blocking anything. Use it to measure a new Guardrail's
   false positives before you enforce it.
 - ``failClosed`` decides what happens when a Guardrail cannot run, for example when its provider
   is unreachable. When false, the default, the failure is recorded and the Guardrail is skipped.
   When true, the text is blocked. Use it for Guardrails whose absence is unacceptable.

Built-in Guardrails
-------------------

Smarter installs the following Guardrails, owned by the Smarter admin user, and shared with every
account. Install them with ``python manage.py add_builtin_guardrails``.

.. list-table::
   :header-rows: 1

   * - Name
     - Stage
     - Category
     - Strategy
     - Action
   * - ``pii_redaction_input``
     - input
     - pii
     - detector
     - redact
   * - ``secrets_redaction_input``
     - input
     - secrets
     - detector
     - redact
   * - ``prompt_injection_keyword_input``
     - input
     - prompt_injection
     - keyword
     - block
   * - ``prompt_injection_llm_judge_input``
     - input
     - prompt_injection
     - llm_judge
     - block
   * - ``jailbreak_semantic_input``
     - input
     - jailbreak
     - semantic
     - flag
   * - ``moderation_input``
     - input
     - toxicity
     - moderation
     - block
   * - ``self_harm_input``
     - input
     - self_harm
     - moderation
     - escalate
   * - ``off_topic_input``
     - input
     - off_topic
     - llm_judge
     - block
   * - ``code_injection_input``
     - input
     - prompt_injection
     - regex
     - flag
   * - ``data_subject_request_input``
     - input
     - compliance
     - keyword
     - escalate
   * - ``pii_leak_output``
     - output
     - pii
     - detector
     - redact
   * - ``secrets_leak_output``
     - output
     - secrets
     - detector
     - redact
   * - ``moderation_output``
     - output
     - toxicity
     - moderation
     - block
   * - ``profanity_output``
     - output
     - toxicity
     - keyword
     - redact
   * - ``regulated_advice_output``
     - output
     - compliance
     - llm_judge
     - flag
   * - ``fabricated_citation_output``
     - output
     - hallucination
     - llm_judge
     - flag (monitor)
   * - ``script_injection_output``
     - output
     - formatting
     - regex
     - redact
   * - ``json_code_fence_output``
     - output
     - formatting
     - regex
     - transform

``off_topic_input`` is a template: copy it, and describe your LLMClient's scope in its judge prompt.

Security Notes
--------------

 - Guardrails reduce risk; they do not remove it. Keyword and regex Guardrails are easily evaded
   by paraphrase or encoding; the model-based strategies are stronger, and slower. Layer both, and
   keep least privilege in the LLMClient's plugins and functions regardless.
 - An ``llm_judge`` Guardrail is itself an LLM, and may be manipulated by the text it judges.
   Smarter tells the judge that the text is untrusted data, and asks for a JSON verdict, and the
   built-in judge prompts quote the text, but a judge should not be the only control against a
   determined attacker.
 - Input Guardrails scan only the user's latest message. The system prompt, and earlier messages,
   were scanned when they were sent.
 - Event excerpts are masked: PII keeps its last four characters, and secrets only their length.
   Nevertheless, restrict access to the GuardrailEvent admin.
 - Start new Guardrails in ``monitor`` mode, and review their events, before you enforce them.

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   guardrail/admin
   guardrail/api
   guardrail/caching
   guardrail/const
   guardrail/exceptions
   guardrail/management
   guardrail/manifest
   guardrail/models
   guardrail/receivers
   guardrail/serializers
   guardrail/services
   guardrail/signals
   guardrail/tasks
   guardrail/utils
   guardrail/views
