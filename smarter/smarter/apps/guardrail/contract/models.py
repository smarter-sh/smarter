"""
Pydantic models of the Guardrails' REST api requests and responses (``/api/v1/guardrails/``).

The REST api's views build their responses from these models, and the Smarter api's OpenAPI
document (:mod:`smarter.apps.api.v1.contract.openapi`) publishes their JSON Schemas.

:class:`GuardrailApiGuardrail` is a Guardrail, as :class:`smarter.apps.guardrail.serializers.GuardrailSerializer`
returned it before the api was modeled, and :class:`GuardrailApiEvent` an event, as
:class:`~smarter.apps.guardrail.serializers.GuardrailEventSerializer` returned it. Clients already
read them, so their shapes are kept: a Guardrail's keys are camelCase, and an event's snake_case.
One value changed: a Guardrail's ``canDelete`` is computed for the requesting user. The serializer
was called without a request, so it was always false.

The models forbid extra fields: the api returns exactly what they declare.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from smarter.apps.account.contract.models import (
    AccountApiModel,
    AccountApiUserProfile,
    MetaDataApiAnnotations,
)
from smarter.apps.account.serializers import user_can_delete
from smarter.apps.provider.services.text_completion.contracts import (
    GuardrailMatch,
    PipelineDisposition,
)

if TYPE_CHECKING:
    from smarter.apps.guardrail.models import Guardrail, GuardrailEvent


GuardrailApiStage = Literal["input", "output", "both"]
"""The choices of ``Guardrail.stage``.

A test fails if the two differ.
"""

GuardrailApiCategory = Literal[
    "pii",
    "secrets",
    "prompt_injection",
    "jailbreak",
    "toxicity",
    "self_harm",
    "hallucination",
    "off_topic",
    "compliance",
    "formatting",
    "custom",
]
"""The choices of ``Guardrail.category``.

A test fails if the two differ.
"""

GuardrailApiStrategy = Literal["regex", "keyword", "detector", "semantic", "moderation", "llm_judge"]
"""The choices of ``Guardrail.strategy``.

A test fails if the two differ.
"""

GuardrailApiAction = Literal["log", "flag", "redact", "transform", "block", "escalate"]
"""The choices of ``Guardrail.action``.

A test fails if the two differ.
"""

GuardrailApiMode = Literal["enforce", "monitor"]
"""The choices of ``Guardrail.mode``.

A test fails if the two differ.
"""

GuardrailApiEventDisposition = Literal[
    "logged", "flagged", "redacted", "transformed", "blocked", "escalated", "monitored", "error"
]
"""The choices of ``GuardrailEvent.disposition``: what a guardrail did.

A test fails if the two differ.
"""


class GuardrailApiGuardrail(AccountApiModel):
    """A Guardrail: a :class:`smarter.apps.guardrail.models.Guardrail`."""

    id: int = Field(..., description="The row's primary key.")
    hashed_id: str = Field(..., description="The Guardrail's hashed id, which its urls use.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="MetaDataModel.name, in snake_case.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    tags: list[str] = Field(default_factory=list, description="MetaDataModel.tags, by name.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    user_profile: AccountApiUserProfile = Field(..., description="The Guardrail's owner.")
    can_delete: bool = Field(
        ...,
        description="Whether the requesting user may delete the Guardrail now: they own it, and no LLMClient uses it.",
    )
    manifest_url: str = Field(..., description="The url of the Guardrail's manifest in the web console.")
    detail_url: Optional[str] = Field(
        None,
        description="The url of the Guardrail's detail in the web console: its manifest, the resources that it uses, "
        "and those that use it.",
    )
    ready: bool = Field(..., description="Whether the Guardrail is configured completely.")
    rfc1034_compliant_name: Optional[str] = Field(None, description="The name, as a DNS label.")
    stage: GuardrailApiStage = Field(
        ..., description="What the Guardrail checks: the user's message, the LLM's reply, or both."
    )
    category: GuardrailApiCategory = Field(..., description="What the Guardrail protects against.")
    strategy: GuardrailApiStrategy = Field(..., description="How the Guardrail detects it.")
    pattern: Optional[str] = Field(None, description="The regular expression of the regex strategy.")
    config: Optional[dict[str, JsonValue]] = Field(None, description="The strategy's configuration.")
    threshold: Optional[float] = Field(None, description="The confidence at which a scoring strategy triggers.")
    action: GuardrailApiAction = Field(..., description="What the Guardrail does when it triggers.")
    replacement: Optional[str] = Field(None, description="The replacement of the redact action.")
    message: Optional[str] = Field(None, description="The message that replaces a blocked text.")
    severity: int = Field(..., ge=0, description="The severity of what the Guardrail detects, from 1 to 5.")
    mode: GuardrailApiMode = Field(..., description="enforce acts. monitor only records what it would do.")
    fail_closed: bool = Field(..., description="Whether an error of the Guardrail blocks the text.")
    priority: int = Field(..., ge=0, description="The order of the Guardrails. Lower runs first.")
    is_active: bool = Field(..., description="Whether the Guardrail runs.")

    @classmethod
    def from_model(cls, guardrail: "Guardrail", user: object = None) -> "GuardrailApiGuardrail":
        """
        The contract's model of a Guardrail.

        :param guardrail: The row, whose ``user_profile`` should be fetched with it.
        :type guardrail: smarter.apps.guardrail.models.Guardrail
        :param user: The requesting user, for ``can_delete``. None may delete nothing.
        :type user: object
        :returns: The model.
        :rtype: GuardrailApiGuardrail
        """
        # pylint: disable=import-outside-toplevel
        from django.urls import reverse

        from smarter.apps.dashboard.resource_detail import resource_detail_url
        from smarter.apps.guardrail.manifest.models.guardrail.const import (
            MANIFEST_KIND as GUARDRAIL_KIND,
        )
        from smarter.apps.guardrail.urls import GuardrailReverseNames

        return cls(
            id=guardrail.pk,
            hashed_id=guardrail.hashed_id,
            created_at=guardrail.created_at,
            updated_at=guardrail.updated_at,
            name=guardrail.name,
            description=guardrail.description,
            version=guardrail.version,
            tags=[tag.name for tag in guardrail.tags.all()],
            annotations=guardrail.annotations,
            user_profile=AccountApiUserProfile.from_model(guardrail.user_profile),
            can_delete=user_can_delete(guardrail, GUARDRAIL_KIND, user),
            detail_url=resource_detail_url(GUARDRAIL_KIND, guardrail.record_locator),
            manifest_url=reverse(
                f"{GuardrailReverseNames.namespace}:{GuardrailReverseNames.detailview}",
                kwargs={"hashed_id": guardrail.hashed_id},
            ),
            ready=guardrail.ready,
            rfc1034_compliant_name=guardrail.rfc1034_compliant_name,
            stage=guardrail.stage,  # type: ignore[arg-type]
            category=guardrail.category,  # type: ignore[arg-type]
            strategy=guardrail.strategy,  # type: ignore[arg-type]
            pattern=guardrail.pattern,
            config=guardrail.config,
            threshold=guardrail.threshold,
            action=guardrail.action,  # type: ignore[arg-type]
            replacement=guardrail.replacement,
            message=guardrail.message,
            severity=guardrail.severity,
            mode=guardrail.mode,  # type: ignore[arg-type]
            fail_closed=guardrail.fail_closed,
            priority=guardrail.priority,
            is_active=guardrail.is_active,
        )


class GuardrailApiSnakeModel(BaseModel):
    """Base class of the guardrail contract's models whose keys are snake_case, as their api returned them."""

    model_config = ConfigDict(extra="forbid")


class GuardrailApiEvent(GuardrailApiSnakeModel):
    """
    A Guardrail's event: a :class:`smarter.apps.guardrail.models.GuardrailEvent`, a record of what it did to a prompt.

    Its keys are snake_case: the serializer that the api used was not camelCase.
    """

    id: int = Field(..., description="The row's primary key.")
    created_at: Optional[datetime] = Field(None, description="When the Guardrail triggered.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    guardrail: Optional[int] = Field(None, description="The Guardrail's id, or null if it was deleted.")
    guardrail_name: str = Field(..., description="The Guardrail's name, kept if it is deleted.")
    llmclient: Optional[str] = Field(None, description="The name of the LLMClient whose prompt triggered it.")
    session_key: Optional[str] = Field(None, description="The chat session.")
    stage: GuardrailApiStage = Field(..., description="Where it triggered: the user's message, or the LLM's reply.")
    category: GuardrailApiCategory
    strategy: GuardrailApiStrategy
    action: GuardrailApiAction
    mode: GuardrailApiMode
    disposition: GuardrailApiEventDisposition = Field(..., description="What the Guardrail did.")
    severity: int = Field(..., ge=0)
    confidence: Optional[float] = Field(None, description="The strategy's confidence.")
    excerpt: Optional[str] = Field(None, description="An excerpt of what matched, masked.")
    rationale: Optional[str] = Field(None, description="Why it triggered, for a person.")
    error: Optional[str] = Field(None, description="The Guardrail's error, if it failed.")
    reviewed: bool = Field(..., description="Whether a person has reviewed the event.")

    @classmethod
    def from_model(cls, event: "GuardrailEvent") -> "GuardrailApiEvent":
        """
        The contract's model of a Guardrail's event.

        :param event: The row, whose ``llmclient`` should be fetched with it.
        :type event: smarter.apps.guardrail.models.GuardrailEvent
        :returns: The model.
        :rtype: GuardrailApiEvent
        """
        return cls(
            id=event.pk,
            created_at=event.created_at,
            updated_at=event.updated_at,
            guardrail=event.guardrail_id,  # type: ignore[attr-defined]
            guardrail_name=event.guardrail_name,
            llmclient=event.llmclient.name if event.llmclient else None,
            session_key=event.session_key,
            stage=event.stage,  # type: ignore[arg-type]
            category=event.category,  # type: ignore[arg-type]
            strategy=event.strategy,  # type: ignore[arg-type]
            action=event.action,  # type: ignore[arg-type]
            mode=event.mode,  # type: ignore[arg-type]
            disposition=event.disposition,  # type: ignore[arg-type]
            severity=event.severity,
            confidence=event.confidence,
            excerpt=event.excerpt,
            rationale=event.rationale,
            error=event.error,
            reviewed=event.reviewed,
        )


class GuardrailApiEvents(GuardrailApiSnakeModel):
    """The response of a Guardrail's events: its name, and its latest events, newest first."""

    guardrail: str = Field(..., description="The Guardrail's name.")
    events: list[GuardrailApiEvent]


class GuardrailApiEvaluateRequest(GuardrailApiSnakeModel):
    """The request body of a dry run of a Guardrail on a text."""

    text: str = Field(..., min_length=1, max_length=20000, description="The text.")
    stage: Literal["input", "output"] = Field(
        "input", description="Whether the text is the user's message (input) or the LLM's reply (output)."
    )


class GuardrailApiFinding(GuardrailApiSnakeModel):
    """What a Guardrail found in a text."""

    confidence: Optional[float] = Field(None, description="The strategy's confidence.")
    rationale: Optional[str] = Field(None, description="Why it triggered, for a person.")
    matches: list[GuardrailMatch] = Field(..., description="Where the text matched.")


class GuardrailApiEvaluation(AccountApiModel):
    """The result of a dry run of a Guardrail on a text.

    It records no events.
    """

    guardrail: str = Field(..., description="The Guardrail's name.")
    stage: Literal["input", "output"]
    triggered: bool = Field(..., description="Whether the Guardrail triggered.")
    disposition: PipelineDisposition = Field(..., description="What would happen to the text.")
    text: str = Field(..., description="The text after the Guardrail's action, e.g. redacted.")
    message: Optional[str] = Field(None, description="The message that would replace a blocked text.")
    error: Optional[str] = Field(None, description="The Guardrail's error, if it failed.")
    duration_ms: Optional[float] = Field(None, description="How long the Guardrail took, in milliseconds.")
    findings: list[GuardrailApiFinding] = Field(..., description="What it found, if it triggered.")


GUARDRAIL_API_MODELS = (
    GuardrailApiGuardrail,
    GuardrailApiEvents,
    GuardrailApiEvaluateRequest,
    GuardrailApiEvaluation,
)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes.

Their dependencies are included with them.
"""

__all__ = [
    "GUARDRAIL_API_MODELS",
    "GuardrailApiAction",
    "GuardrailApiCategory",
    "GuardrailApiEvaluateRequest",
    "GuardrailApiEvaluation",
    "GuardrailApiEvent",
    "GuardrailApiEventDisposition",
    "GuardrailApiEvents",
    "GuardrailApiFinding",
    "GuardrailApiGuardrail",
    "GuardrailApiMode",
    "GuardrailApiSnakeModel",
    "GuardrailApiStage",
    "GuardrailApiStrategy",
]
