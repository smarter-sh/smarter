"""
Pydantic models of the Smarter Journal api contract.

They describe the envelope that :class:`smarter.lib.journal.http.SmarterJournaledJsonResponse`
adds to every journaled response, the error body of
:class:`smarter.lib.journal.http.SmarterJournaledJsonErrorResponse`, and a journal entry, a
:class:`smarter.lib.journal.models.SAMJournal` row.

These models are the contract's single source of truth:

- the journaled responses are built from them, by :mod:`smarter.lib.journal.http`,
- the JSON Schema in ``journal-contract.schema.json`` is generated from them (``manage.py
  export_journal_contract_schema``), for the clients that read journaled responses, such as the
  ``smarter`` cli.

The envelope and the error body allow extra fields, because each view adds its own data beside
them. The model of a journal entry (:class:`SAMJournalApiOrmModel`) has exactly the row's fields.
Adding a field is backward compatible. Removing or renaming one that is declared here is not.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from smarter.common.api import SmarterApiVersions

from .const import JOURNAL_KEY_PATTERN

if TYPE_CHECKING:
    from smarter.lib.journal.models import SAMJournal


SAMJournalApiJson = JsonValue
"""A value that is stored, and returned, as arbitrary JSON, e.g. a journal entry's request and response documents."""

SAMJournalApiThing = Literal[
    "Account",
    "ApiConnection",
    "ApiPlugin",
    "SmarterAuthToken",
    "Budget",
    "CustomDomain",
    "Guardrail",
    "ImageSearchPlugin",
    "LLMClient",
    "MCPClient",
    "Orchestrator",
    "Prompt",
    "ChatConfig",
    "Proxy",
    "Provider",
    "Secret",
    "SkillPlugin",
    "SqlConnection",
    "SqlPlugin",
    "Plugin",
    "User",
    "Vectorsearch",
    "Vectorstore",
    "WebsearchPlugin",
]
"""A journal entry's ``thing``: the choices of ``SAMJournal.thing``.

See :meth:`smarter.lib.journal.enum.SmarterJournalThings.choices`.
"""

SAMJournalApiCommand = Literal[
    "apply",
    "prompt",
    "chat_config",
    "delete",
    "deploy",
    "describe",
    "get",
    "journal",
    "logs",
    "example_manifest",
    "status",
    "json_schema",
    "version",
    "undeploy",
    "validate",
    "whoami",
    "resources",
]
"""A journal entry's ``command``: the choices of ``SAMJournal.command``.

See :meth:`smarter.lib.journal.enum.SmarterJournalCliCommands.choices`.
"""


class SAMJournalApiModel(BaseModel):
    """Base class of the contract's models of responses, which allow extra fields."""

    model_config = ConfigDict(extra="allow")


# ------------------------------------------------------------------------------
# journaled responses
# ------------------------------------------------------------------------------


class SAMJournalApiMetadata(SAMJournalApiModel):
    """
    The ``metadata`` of a journaled response: its command and thing, and, when the journal is enabled, the key of its journal entry.

    ``command`` and ``thing`` are the strings of the values that the view passed, which may be
    ``"None"`` when it passed none, so they are not limited to the journal's choices.
    """

    command: str = Field(..., description="The journal's command, e.g. apply.")
    thing: str = Field(..., description="The journal's thing, e.g. Guardrail.")
    key: Optional[str] = Field(
        None,
        pattern=JOURNAL_KEY_PATTERN,
        description="The key of the response's journal entry. Absent while the journal is disabled, or if the entry could not be saved.",
    )


class SAMJournalApiEnvelope(SAMJournalApiModel):
    """The fields that every journaled response adds beside the view's own data."""

    api: str = Field(SmarterApiVersions.V1, description='The api version, e.g. "smarter.sh/v1".')
    metadata: SAMJournalApiMetadata = Field(..., description="The journal's command and thing, and its entry's key.")

    @classmethod
    def build(cls, command: object, thing: object) -> "SAMJournalApiEnvelope":
        """
        The envelope of a response, without a journal key.

        :param command: The command that the view passed, e.g. a ``SmarterJournalCliCommands``, a string, or None.
        :type command: object
        :param thing: The thing that the view passed, e.g. a ``SmarterJournalThings``, a string, or None.
        :type thing: object
        :returns: The envelope.
        :rtype: SAMJournalApiEnvelope
        """
        return cls(metadata=SAMJournalApiMetadata(command=str(command), thing=str(thing)))

    def dump(self) -> dict[str, JsonValue]:
        """
        The envelope as the JSON keys that a journaled response adds: ``api`` and ``metadata``.

        The metadata's ``key`` is left out until the journal entry is saved.

        :returns: The envelope's keys.
        :rtype: dict[str, JsonValue]
        """
        return self.model_dump(mode="json", exclude_none=True)


class SAMJournalApiErrorBody(SAMJournalApiModel):
    """
    The ``error`` of a journaled error response: the same shape for every error of the cli and the other journaled apis.

    The field names are the values of :class:`smarter.lib.journal.enum.SmarterJournalApiResponseErrorKeys`.
    """

    errorClass: str = Field(..., description="The name of the exception's class, e.g. SAMBrokerErrorNotFound.")
    stacktrace: Optional[str] = Field(
        None, description="The stack trace. Left out of the responses that a browser may receive."
    )
    description: Optional[str] = Field(None, description="A human-readable description of the error.")
    status: int = Field(..., description="The http status.")
    args: SAMJournalApiJson = Field(..., description="The exception's arguments, or the request's url.")
    cause: str = Field(..., description="The exception's cause, e.g. 'ValueError: ...', or 'Python Exception'.")
    context: str = Field(..., description="The exception's context, or the response's thing and command.")
    thing: str = Field(..., description="The journal's thing, e.g. Guardrail.")
    command: str = Field(..., description="The journal's command, e.g. describe.")


class SAMJournalApiErrorResponse(SAMJournalApiModel):
    """
    The body of a journaled error response.

    :class:`SAMJournalApiEnvelope`'s ``api`` and ``metadata`` are added beside ``error``.
    """

    error: SAMJournalApiErrorBody

    def dump(self, include_stack_trace: bool = True) -> dict[str, JsonValue]:
        """
        The error response's JSON.

        :param include_stack_trace: Whether the error includes its ``stacktrace``.
        :type include_stack_trace: bool
        :returns: The response's ``error`` key.
        :rtype: dict[str, JsonValue]
        """
        exclude = None if include_stack_trace else {"error": {"stacktrace"}}
        return self.model_dump(mode="json", exclude=exclude)


class SAMJournalApiResponse(SAMJournalApiEnvelope):
    """A journaled response: the envelope, beside the view's own data, e.g. ``data`` or ``error``."""

    error: Optional[SAMJournalApiErrorBody] = Field(None, description="The error of an error response.")


# ------------------------------------------------------------------------------
# journal entries
# ------------------------------------------------------------------------------


class SAMJournalApiOrmModel(BaseModel):
    """
    A journal entry: a :class:`smarter.lib.journal.models.SAMJournal` row.

    Its fields are exactly the row's fields, so extra fields are forbidden. It is built from the row by
    :meth:`from_model`.
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., pattern=JOURNAL_KEY_PATTERN, description="SAMJournal.key, the entry's primary key.")
    created_at: Optional[datetime] = Field(None, description="SAMJournal.created_at.")
    user: Optional[int] = Field(None, description="SAMJournal.user: the user's id, or null for an anonymous request.")
    thing: SAMJournalApiThing = Field(..., description="SAMJournal.thing.")
    command: SAMJournalApiCommand = Field(..., description="SAMJournal.command.")
    request: SAMJournalApiJson = Field(..., description="SAMJournal.request: the serialized http request.")
    response: SAMJournalApiJson = Field(..., description="SAMJournal.response: the response's JSON body.")
    status_code: int = Field(..., ge=0, le=65535, description="SAMJournal.status_code: the http status.")

    @classmethod
    def from_model(cls, journal: "SAMJournal") -> "SAMJournalApiOrmModel":
        """
        The model of a journal entry.

        :param journal: The journal entry.
        :type journal: SAMJournal
        :returns: Its model.
        :rtype: SAMJournalApiOrmModel
        """
        return cls(
            key=journal.key,
            created_at=journal.created_at,
            user=journal.user_id,  # type: ignore[attr-defined]
            thing=journal.thing,  # type: ignore[arg-type]
            command=journal.command,  # type: ignore[arg-type]
            request=journal.request,
            response=journal.response,
            status_code=journal.status_code,
        )


CONTRACT_MODELS: tuple[type[BaseModel], ...] = (
    SAMJournalApiEnvelope,
    SAMJournalApiErrorResponse,
    SAMJournalApiResponse,
    SAMJournalApiOrmModel,
)
"""The models whose JSON Schema is exported.

Their dependencies are exported with them.
"""

__all__ = [
    "CONTRACT_MODELS",
    "SAMJournalApiCommand",
    "SAMJournalApiEnvelope",
    "SAMJournalApiErrorBody",
    "SAMJournalApiErrorResponse",
    "SAMJournalApiJson",
    "SAMJournalApiMetadata",
    "SAMJournalApiModel",
    "SAMJournalApiOrmModel",
    "SAMJournalApiResponse",
    "SAMJournalApiThing",
]
