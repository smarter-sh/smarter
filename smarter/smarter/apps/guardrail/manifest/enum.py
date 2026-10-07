"""
Smarter API Guardrail Manifest - enumerated datatypes.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.lib.manifest.enum import SmarterEnumAbstract


class SAMGuardrailStage(SmarterEnumAbstract):
    """
    When a guardrail runs.

    - ``input``: on the user's message, before it is sent to the LLM.
    - ``output``: on the LLM's reply, before it is returned to the user.
    - ``both``: on both.
    """

    INPUT = "input"
    OUTPUT = "output"
    BOTH = "both"


class SAMGuardrailCategory(SmarterEnumAbstract):
    """The risk that a guardrail addresses.

    It classifies findings, and does not change behavior.
    """

    PII = "pii"
    SECRETS = "secrets"
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    TOXICITY = "toxicity"
    SELF_HARM = "self_harm"
    HALLUCINATION = "hallucination"
    OFF_TOPIC = "off_topic"
    COMPLIANCE = "compliance"
    FORMATTING = "formatting"
    CUSTOM = "custom"


class SAMGuardrailStrategy(SmarterEnumAbstract):
    """
    How a guardrail detects what it guards against.

    - ``regex``: a regular expression.
    - ``keyword``: a list of words or phrases.
    - ``detector``: built-in, validated detectors of personal data and secrets, e.g. credit
      card numbers that pass the Luhn check.
    - ``semantic``: embedding similarity to reference examples.
    - ``moderation``: an LLM provider's moderation model, e.g. OpenAI's omni-moderation.
    - ``llm_judge``: an LLM that judges the text, with a prompt.

    ``regex``, ``keyword`` and ``detector`` are deterministic, fast and free. The others call
    an LLM provider, and add latency and cost to each prompt.
    """

    REGEX = "regex"
    KEYWORD = "keyword"
    DETECTOR = "detector"
    SEMANTIC = "semantic"
    MODERATION = "moderation"
    LLM_JUDGE = "llm_judge"

    @classmethod
    def scored(cls) -> list[str]:
        """Return the strategies that produce a confidence score, and use ``threshold``."""
        return [cls.SEMANTIC.value, cls.MODERATION.value, cls.LLM_JUDGE.value]

    @classmethod
    def locating(cls) -> list[str]:
        """Return the strategies that locate the text they match, as redact and transform require."""
        return [cls.REGEX.value, cls.KEYWORD.value, cls.DETECTOR.value]


class SAMGuardrailAction(SmarterEnumAbstract):
    """
    What a guardrail does when it triggers.

    - ``log``: record the event only.
    - ``flag``: record the event for review, and continue.
    - ``redact``: replace every match with ``replacement``, and continue.
    - ``transform``: replace every match with ``replacement``, which for the regex strategy
      may refer to groups, e.g. ``\\1``, and continue.
    - ``block``: stop, and return ``message`` instead of the LLM's reply.
    - ``escalate``: record the event for human review, notify reviewers, and continue.
    """

    LOG = "log"
    FLAG = "flag"
    REDACT = "redact"
    TRANSFORM = "transform"
    BLOCK = "block"
    ESCALATE = "escalate"


class SAMGuardrailMode(SmarterEnumAbstract):
    """
    Whether a guardrail acts.

    - ``enforce``: it takes its action.
    - ``monitor``: it only records what its action would have been, to evaluate a new
      guardrail against real traffic before enforcing it.
    """

    ENFORCE = "enforce"
    MONITOR = "monitor"


class SAMGuardrailDetector(SmarterEnumAbstract):
    """The built-in detectors of the ``detector`` strategy."""

    CREDIT_CARD = "credit_card"
    US_SSN = "us_ssn"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    IP_ADDRESS = "ip_address"
    IBAN = "iban"
    AWS_ACCESS_KEY = "aws_access_key"
    PRIVATE_KEY = "private_key"
    API_KEY = "api_key"
    JWT = "jwt"
    PASSWORD_ASSIGNMENT = "password_assignment"


class SAMGuardrailModerationCategory(SmarterEnumAbstract):
    """The categories of OpenAI's moderation models."""

    HARASSMENT = "harassment"
    HARASSMENT_THREATENING = "harassment/threatening"
    HATE = "hate"
    HATE_THREATENING = "hate/threatening"
    ILLICIT = "illicit"
    ILLICIT_VIOLENT = "illicit/violent"
    SELF_HARM = "self-harm"
    SELF_HARM_INTENT = "self-harm/intent"
    SELF_HARM_INSTRUCTIONS = "self-harm/instructions"
    SEXUAL = "sexual"
    SEXUAL_MINORS = "sexual/minors"
    VIOLENCE = "violence"
    VIOLENCE_GRAPHIC = "violence/graphic"
