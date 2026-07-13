"""Pydantic contracts for the Guardrail service.

These model the two shapes the Harness hands us — the OpenAI-style
pre-completion request and post-completion response — plus the result
types the pipeline hands back to the Harness. Keeping these as Pydantic
models (rather than raw ``dict`` objects) gives us validation at the
boundary and typed access everywhere downstream, consistent with the
rest of the SAM stack.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ----------------------------------------------------------------------
# Pipeline stage
# ----------------------------------------------------------------------
class GuardrailStage(str, Enum):
    """Which side of the model call the pipeline is running on.

    Mirrors :class:`smarter.apps.guardrail.models.GuardrailType`, but
    named distinctly since a :class:`~smarter.apps.guardrail.models.Guardrail`
    row with ``guardrail_type=BOTH`` runs on *both* stages, while a given
    pipeline invocation is always exactly one.

    :cvar PRE: The pre-completion request, before it is sent to the LLM
        provider.
    :cvar POST: The post-completion response, after it comes back from
        the LLM provider.
    """

    PRE = "pre"
    POST = "post"


# ----------------------------------------------------------------------
# Inbound payload shapes (OpenAI chat.completions wire format)
# ----------------------------------------------------------------------
class ChatMessage(BaseModel):
    """A single entry in a pre-completion request's ``messages`` list.

    :ivar role: The message role, e.g. ``"user"``, ``"system"``, or
        ``"assistant"``.
    :vartype role: str
    :ivar content: The message text, or ``None`` if the message carries
        no plain-text content (e.g. a tool-call-only message).
    :vartype content: str or None
    :ivar name: Optional name qualifying the role, per the OpenAI
        chat-completions schema.
    :vartype name: str or None
    """

    model_config = ConfigDict(extra="allow")

    role: str
    content: str | None = None
    name: str | None = None


class FunctionParameter(BaseModel):
    """JSON Schema describing a callable function's parameters.

    :ivar type: The JSON Schema type, typically ``"object"``.
    :vartype type: str or None
    :ivar properties: The JSON Schema ``properties`` mapping for the
        function's parameters.
    :vartype properties: dict[str, typing.Any]
    :ivar required: Names of parameters that are required.
    :vartype required: list[str]
    """

    model_config = ConfigDict(extra="allow")

    type: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class FunctionSpec(BaseModel):
    """A single entry in a pre-completion request's ``functions`` list.

    :ivar name: The function's name, as the model would reference it in
        a function call.
    :vartype name: str
    :ivar description: A natural-language description of what the
        function does.
    :vartype description: str or None
    :ivar parameters: The function's parameter schema.
    :vartype parameters: FunctionParameter or None
    """

    model_config = ConfigDict(extra="allow")

    name: str
    description: str | None = None
    parameters: FunctionParameter | None = None


class PreCompletionPayload(BaseModel):
    """The request body the Harness is about to send to the LLM provider.

    :ivar model: The model identifier the Harness intends to call, e.g.
        ``"gpt-4o-mini"``.
    :vartype model: str
    :ivar temperature: The sampling temperature for the request, if set.
    :vartype temperature: float or None
    :ivar max_tokens: The maximum completion length, if set.
    :vartype max_tokens: int or None
    :ivar messages: The conversation history being sent to the model.
    :vartype messages: list[ChatMessage]
    :ivar functions: Callable functions made available to the model for
        this request.
    :vartype functions: list[FunctionSpec]
    """

    model_config = ConfigDict(extra="allow")

    model: str
    temperature: float | None = None
    max_tokens: int | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    functions: list[FunctionSpec] = Field(default_factory=list)


class UsageDetails(BaseModel):
    """Fine-grained token accounting for a single usage category.

    :ivar audio_tokens: Tokens attributable to audio content.
    :vartype audio_tokens: int
    :ivar cached_tokens: Tokens served from a prompt cache.
    :vartype cached_tokens: int
    :ivar accepted_prediction_tokens: Predicted-output tokens that were
        accepted.
    :vartype accepted_prediction_tokens: int
    :ivar reasoning_tokens: Tokens spent on internal reasoning.
    :vartype reasoning_tokens: int
    :ivar rejected_prediction_tokens: Predicted-output tokens that were
        rejected.
    :vartype rejected_prediction_tokens: int
    """

    model_config = ConfigDict(extra="allow")

    audio_tokens: int = 0
    cached_tokens: int = 0
    accepted_prediction_tokens: int = 0
    reasoning_tokens: int = 0
    rejected_prediction_tokens: int = 0


class Usage(BaseModel):
    """Token usage for a post-completion response.

    :ivar completion_tokens: Tokens generated in the completion.
    :vartype completion_tokens: int
    :ivar prompt_tokens: Tokens consumed by the prompt.
    :vartype prompt_tokens: int
    :ivar total_tokens: ``prompt_tokens + completion_tokens``.
    :vartype total_tokens: int
    :ivar completion_tokens_details: Breakdown of ``completion_tokens``.
    :vartype completion_tokens_details: UsageDetails or None
    :ivar prompt_tokens_details: Breakdown of ``prompt_tokens``.
    :vartype prompt_tokens_details: UsageDetails or None
    """

    model_config = ConfigDict(extra="allow")

    completion_tokens: int = 0
    prompt_tokens: int = 0
    total_tokens: int = 0
    completion_tokens_details: UsageDetails | None = None
    prompt_tokens_details: UsageDetails | None = None


class ChoiceMessage(BaseModel):
    """The message body of a single post-completion choice.

    :ivar role: The message role, typically ``"assistant"``.
    :vartype role: str
    :ivar content: The completion text, or ``None`` if the model
        produced no plain-text content (e.g. a tool-call-only response).
    :vartype content: str or None
    :ivar refusal: A refusal message, if the model declined to answer.
    :vartype refusal: str or None
    :ivar function_call: A legacy single function call, if the model
        invoked one.
    :vartype function_call: dict[str, typing.Any] or None
    :ivar tool_calls: One or more tool calls, if the model invoked any.
    :vartype tool_calls: list[dict[str, typing.Any]] or None
    """

    model_config = ConfigDict(extra="allow")

    role: str
    content: str | None = None
    refusal: str | None = None
    function_call: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] | None = None


class Choice(BaseModel):
    """A single completion choice within a post-completion response.

    :ivar index: The choice's position in the ``choices`` list.
    :vartype index: int
    :ivar finish_reason: Why the model stopped generating, e.g.
        ``"stop"`` or ``"length"``.
    :vartype finish_reason: str or None
    :ivar message: The generated message for this choice.
    :vartype message: ChoiceMessage
    """

    model_config = ConfigDict(extra="allow")

    index: int
    finish_reason: str | None = None
    message: ChoiceMessage


class PostCompletionPayload(BaseModel):
    """The response body the Harness got back from the LLM provider.

    :ivar id: The provider-assigned completion ID.
    :vartype id: str or None
    :ivar model: The model that actually served the request.
    :vartype model: str or None
    :ivar choices: The generated completion choices.
    :vartype choices: list[Choice]
    :ivar usage: Token usage for the request.
    :vartype usage: Usage or None
    :ivar api: The API identifier that produced this response, per the
        SAM wire format (e.g. ``"smarter.sh/v1"``).
    :vartype api: str or None
    :ivar metadata: Provider- or platform-specific metadata attached to
        the response.
    :vartype metadata: dict[str, typing.Any]
    """

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    model: str | None = None
    choices: list[Choice] = Field(default_factory=list)
    usage: Usage | None = None
    api: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ----------------------------------------------------------------------
# Text extraction — the flattened surface guardrails actually scan
# ----------------------------------------------------------------------
class TextSegment(BaseModel):
    """A single scannable string pulled out of a pre/post payload.

    :ivar path: A JSONPath-like breadcrumb, e.g. ``"messages[0].content"``,
        used by ``REDACT``/``TRANSFORM`` actions to know where to write
        results back, and by findings to report where a match occurred.
    :vartype path: str
    :ivar text: The segment's scannable text.
    :vartype text: str
    """

    path: str
    text: str


# ----------------------------------------------------------------------
# Findings / outcomes
# ----------------------------------------------------------------------
class GuardrailFinding(BaseModel):
    """What a single guardrail strategy discovered about a single segment.

    :ivar guardrail_id: Primary key of the originating
        :class:`~smarter.apps.guardrail.models.Guardrail` row.
    :vartype guardrail_id: int
    :ivar guardrail_name: Name of the originating guardrail, for
        logging/display without a further lookup.
    :vartype guardrail_name: str
    :ivar category: The guardrail's
        :class:`~smarter.apps.guardrail.models.GuardrailCategory` value.
    :vartype category: str
    :ivar match_strategy: The guardrail's
        :class:`~smarter.apps.guardrail.models.MatchStrategy` value.
    :vartype match_strategy: str
    :ivar action: The guardrail's
        :class:`~smarter.apps.guardrail.models.GuardrailAction` value.
    :vartype action: str
    :ivar severity: The guardrail's configured severity, ``1`` (low) to
        ``5`` (critical).
    :vartype severity: int
    :ivar triggered: Whether the strategy considered this segment a
        match.
    :vartype triggered: bool
    :ivar confidence: The strategy's confidence score, for scored
        strategies (``semantic``, ``model``, ``llm_judge``).
    :vartype confidence: float or None
    :ivar matched_text: The specific text that triggered the finding,
        when available.
    :vartype matched_text: str or None
    :ivar segment_path: The :attr:`TextSegment.path` this finding
        applies to, set only when ``triggered`` is ``True``.
    :vartype segment_path: str or None
    :ivar rationale: A human-readable explanation of the finding.
    :vartype rationale: str or None
    """

    guardrail_id: int
    guardrail_name: str
    category: str
    match_strategy: str
    action: str
    severity: int
    triggered: bool
    confidence: float | None = None
    matched_text: str | None = None
    segment_path: str | None = None
    rationale: str | None = None


class GuardrailOutcome(BaseModel):
    """Result of running one Guardrail row against the full payload.

    :ivar guardrail_id: Primary key of the evaluated
        :class:`~smarter.apps.guardrail.models.Guardrail` row.
    :vartype guardrail_id: int
    :ivar guardrail_name: Name of the evaluated guardrail.
    :vartype guardrail_name: str
    :ivar is_blocking: The guardrail's ``is_blocking`` flag at the time
        of evaluation.
    :vartype is_blocking: bool
    :ivar priority: The guardrail's ``priority`` at the time of
        evaluation; lower runs first.
    :vartype priority: int
    :ivar findings: One finding per scanned segment.
    :vartype findings: list[GuardrailFinding]
    :ivar error: A description of any error raised while evaluating
        this guardrail, or ``None`` if evaluation succeeded.
    :vartype error: str or None
    :ivar duration_ms: Wall-clock time spent evaluating this guardrail,
        in milliseconds.
    :vartype duration_ms: float or None
    """

    guardrail_id: int
    guardrail_name: str
    is_blocking: bool
    priority: int
    findings: list[GuardrailFinding] = Field(default_factory=list)
    error: str | None = None
    duration_ms: float | None = None

    @property
    def triggered(self) -> bool:
        """Whether any finding for this guardrail triggered.

        :returns: ``True`` if at least one entry in :attr:`findings` has
            ``triggered=True``.
        :rtype: bool
        """
        return any(f.triggered for f in self.findings)


class PipelineDisposition(str, Enum):
    """Final verdict the pipeline hands back to the Harness.

    Ordered from least to most severe; see
    :data:`smarter.apps.guardrail.services.pipeline._DISPOSITION_PRECEDENCE`
    for how multiple triggered guardrails are folded into one value.

    :cvar ALLOWED: No guardrail triggered, or only shadow-mode
        (``is_blocking=False``) guardrails triggered.
    :cvar FLAGGED: A guardrail triggered with action ``FLAG``.
    :cvar REDACTED: A guardrail triggered with action ``REDACT``.
    :cvar TRANSFORMED: A guardrail triggered with action ``TRANSFORM``.
    :cvar ESCALATED: A guardrail triggered with action ``ESCALATE``.
    :cvar BLOCKED: A guardrail triggered with action ``BLOCK``; the
        request or response was withheld.
    """

    ALLOWED = "allowed"
    FLAGGED = "flagged"
    REDACTED = "redacted"
    TRANSFORMED = "transformed"
    BLOCKED = "blocked"
    ESCALATED = "escalated"


class PipelineResult(BaseModel):
    """What ``GuardrailPipeline.run_pre``/``run_post`` return to the Harness.

    :ivar stage: Which stage this result is for.
    :vartype stage: GuardrailStage
    :ivar disposition: The overall verdict across every guardrail
        evaluated for this call.
    :vartype disposition: PipelineDisposition
    :ivar payload: The (possibly redacted/transformed) payload the
        Harness should use going forward; identical to the input
        payload when ``disposition`` is ``ALLOWED``.
    :vartype payload: dict[str, typing.Any]
    :ivar fallback_message: The user-facing message to show when
        ``disposition`` is ``BLOCKED``; ``None`` otherwise.
    :vartype fallback_message: str or None
    :ivar outcomes: The per-guardrail results that produced this
        verdict, in priority order.
    :vartype outcomes: list[GuardrailOutcome]
    :ivar guardrails_evaluated: The number of guardrails evaluated for
        this call, i.e. ``len(outcomes)``.
    :vartype guardrails_evaluated: int
    :ivar total_duration_ms: Total wall-clock time spent evaluating all
        guardrails for this call, in milliseconds.
    :vartype total_duration_ms: float or None
    :ivar request_uid: The caller-supplied request identifier, if any,
        for correlating this result with logs/traces.
    :vartype request_uid: str or None
    """

    model_config = ConfigDict(extra="allow")

    stage: GuardrailStage
    disposition: PipelineDisposition
    payload: dict[str, Any]
    fallback_message: str | None = None
    outcomes: list[GuardrailOutcome] = Field(default_factory=list)
    guardrails_evaluated: int = 0
    total_duration_ms: float | None = None
    request_uid: str | None = None

    @property
    def blocked(self) -> bool:
        """Whether the pipeline blocked this request or response.

        :returns: ``True`` if :attr:`disposition` is
            :attr:`PipelineDisposition.BLOCKED`.
        :rtype: bool
        """
        return self.disposition == PipelineDisposition.BLOCKED

    @property
    def triggered_findings(self) -> list[GuardrailFinding]:
        """Every triggered finding across all evaluated guardrails.

        :returns: The flattened, triggered-only findings from
            :attr:`outcomes`, in outcome order.
        :rtype: list[GuardrailFinding]
        """
        return [f for o in self.outcomes for f in o.findings if f.triggered]


__all__ = [
    "GuardrailStage",
    "ChatMessage",
    "FunctionParameter",
    "FunctionSpec",
    "PreCompletionPayload",
    "UsageDetails",
    "Usage",
    "ChoiceMessage",
    "Choice",
    "PostCompletionPayload",
    "TextSegment",
    "GuardrailFinding",
    "GuardrailOutcome",
    "PipelineDisposition",
    "PipelineResult",
]
