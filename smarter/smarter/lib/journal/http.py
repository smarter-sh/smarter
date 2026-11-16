"""
Journaled JSON responses of the Smarter api, and its common error response.

Every response of the cli api, and of other Smarter apis, is a :class:`SmarterJournaledJsonResponse`
or a :class:`SmarterJournaledJsonErrorResponse`. Each adds the api version and metadata envelope to
its data, and, while the ``ENABLE_JOURNAL`` switch is on, queues the request and response to be
saved as a :class:`~smarter.lib.journal.models.SAMJournal` entry by a Celery worker
(:func:`smarter.lib.journal.tasks.create_journal_entry`).
"""

from collections.abc import Sequence
from http import HTTPStatus
from json import JSONEncoder
from typing import Any, Optional, Union

from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from pydantic import JsonValue

from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.mixins import SmarterHelperMixin
from smarter.common.utils import hash_factory, is_authenticated_request
from smarter.lib import json, logging
from smarter.lib.django import waffle
from smarter.lib.django.http.serializers import (
    HttpAnonymousRequestSerializer,
    HttpAuthenticatedRequestSerializer,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.json import SmarterJSONEncoder
from smarter.lib.typing import SmarterDictType

from .contract.models import (
    SAMJournalApiEnvelope,
    SAMJournalApiErrorBody,
    SAMJournalApiErrorResponse,
    SAMJournalApiMetadata,
)
from .enum import SmarterJournalCliCommands, SmarterJournalThings
from .signals import journal_entry_failed
from .sources import SAMJournalSource
from .tasks import SAMJournalEntryRecord, queue_journal_entry

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

JSON_RESPONSE_KWARGS = frozenset({"content_type", "status", "headers", "reason"})
"""The keyword arguments of a journaled response that are passed on to :class:`django.http.JsonResponse`."""


def journal_user_id(request: HttpRequest) -> Optional[int]:
    """
    Return the id of the request's user, for ``SAMJournal.user``.

    :param request: The request.
    :returns: The user's id, or None for an anonymous request, or a request without a user, e.g. an
        ``ASGIRequest`` that no authentication middleware saw.
    """
    # an authenticated request has a user, who isn't anonymous.
    if not is_authenticated_request(request):
        return None
    user_id: Optional[int] = request.user.pk
    return user_id


def journal_field(value: Optional[Union[SmarterJournalThings, SmarterJournalCliCommands, str]]) -> str:
    """
    Return the value of ``SAMJournal.thing`` or ``SAMJournal.command``.

    :param value: The thing or command that the view passed.
    :returns: The value as a string, as Django would save it, or blank if the view passed none: the
        columns are blank, not NULL.
    """
    if value is None:
        return ""
    return str(value)


def json_response_kwargs(kwargs: SmarterDictType) -> SmarterDictType:
    """
    Return the keyword arguments that :class:`django.http.JsonResponse` accepts.

    :param kwargs: The keyword arguments of a journaled response.
    :returns: Those named in :data:`JSON_RESPONSE_KWARGS`. The rest are ignored.
    """
    response_kwargs: SmarterDictType = {}
    for key, value in kwargs.items():
        if key in JSON_RESPONSE_KWARGS:
            response_kwargs[key] = value
    return response_kwargs


class SmarterJournaledJsonResponse(JsonResponse, SmarterHelperMixin):
    """
    An enhanced HTTP response class for the Smarter API that augments standard Django JSON responses with additional manifest structure and metadata.

    This class is designed to provide a consistent response format for all Smarter API endpoints,
    embedding contextual information about the request and operation performed. It automatically
    attaches metadata such as the API version, the entity ("thing") being operated on, and the
    command executed. When journaling is enabled, it also queues a corresponding journal entry,
    capturing the request, response, user, and status code for audit and traceability. The entry's
    key is chosen, and returned in the metadata, before a Celery worker saves the entry, so the entry
    may not exist yet when the client receives the response.

    Smarter-specific parameters include the original Django request object, the noun ("thing") being
    journaled, the command performed, and the API response data. Standard Django JsonResponse parameters
    such as ``data``, ``encoder``, ``safe``, and ``json_dumps_params`` are also supported.

    **Example:**

    The response of a ``describe`` of a Guardrail, beside the view's own ``data``::

        {
            "data": {...},
            "api": "smarter.sh/v1",
            "metadata": {
                "command": "describe",
                "thing": "Guardrail",
                "key": "4f1c...e9a2"
            }
        }

    The metadata's ``key`` is the journal entry's key: it is absent while the journal is disabled, and
    when the entry could be neither queued nor saved.

    **See also:**

    - :doc:`/smarter-framework/developer-reference/smarter-journal/model` for the database model used
      to store journal entries.
    - :class:`django.http.JsonResponse` for inherited response behavior.
    - :func:`smarter.common.utils.hash_factory` for key generation.
    - :mod:`smarter.lib.django.http.serializers` for request serialization.
    - :class:`smarter.lib.journal.contract.models.SAMJournalApiEnvelope`, the contract of the ``api``
      and ``metadata`` keys.

    :param request: The original Django request object.
    :param data: The response data. A dict gets the ``api`` and ``metadata`` keys. A list is sent as
        it is, and anything else is wrapped as ``{"response": data}`` first.
    :param encoder: JSON encoder class. Defaults to :class:`smarter.lib.json.SmarterJSONEncoder`.
    :param safe: Controls if only ``dict`` objects may be serialized. Defaults to ``True``, and only
        applies when ``data`` is a dict.
    :param thing: The resource or entity being operated on (noun).
    :param command: The CLI command executed on the resource.
    :param json_dumps_params: Additional kwargs for ``json.dumps()``.
    :param status: The HTTP status code. Defaults to 200.
    :param journal_sources: The parts of ``data`` that Smarter has already saved, e.g. a chat thread,
        which the journal's worker reads from the database instead of receiving them through the
        Celery broker. See :mod:`smarter.lib.journal.sources`.
    :param kwargs: Of these, only ``content_type``, ``status``, ``headers`` and ``reason`` are passed
        to :class:`django.http.JsonResponse`. The rest are ignored.
    """

    # the arguments of JsonResponse, and the journal's.
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        request: HttpRequest,
        data: Any,
        encoder: type[JSONEncoder] = SmarterJSONEncoder,
        safe: bool = True,
        thing: Optional[Union[SmarterJournalThings, str]] = None,
        command: Optional[SmarterJournalCliCommands] = None,
        json_dumps_params: Optional[SmarterDictType] = None,
        status: int = HTTPStatus.OK.value,
        journal_sources: Sequence[SAMJournalSource] = (),
        **kwargs,
    ):
        if not isinstance(data, (dict, list)):
            # wrap any other data, e.g. a string, before adding the api version and metadata to it.
            data = {"response": data}
        envelope = SAMJournalApiEnvelope.build(command=command, thing=thing)
        if isinstance(data, dict):
            data.update(envelope.dump())

        if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_JOURNAL):
            key = self.journal(request, data, thing, command, status, journal_sources)
            if key is not None and isinstance(data, dict):
                # add the journal's key to the metadata, which keeps its command and thing.
                envelope.metadata = SAMJournalApiMetadata(
                    command=envelope.metadata.command,
                    thing=envelope.metadata.thing,
                    key=key,
                )
                data.update(envelope.dump())

        response_kwargs = json_response_kwargs(kwargs)
        is_safe = safe and isinstance(data, dict)
        super().__init__(
            data=data,
            encoder=encoder,
            safe=is_safe,
            json_dumps_params=json_dumps_params,
            status=status,
            **response_kwargs,
        )

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def journal(
        self,
        request: HttpRequest,
        data: Union[SmarterDictType, list[Any]],
        thing: Optional[Union[SmarterJournalThings, str]],
        command: Optional[SmarterJournalCliCommands],
        status: int,
        journal_sources: Sequence[SAMJournalSource],
    ) -> Optional[str]:
        """
        Queue the response's journal entry, to be saved by a Celery worker.

        The entry's key is chosen now, so that the response can return it. If the entry can be neither
        queued nor saved, ``journal_entry_failed`` is sent, whose receiver logs the gap in the journal,
        and the response is returned without a key.

        :param request: The request.
        :param data: The response's data, with its envelope.
        :param thing: The resource or entity being operated on.
        :param command: The command executed on the resource.
        :param status: The http status code.
        :param journal_sources: The parts of ``data`` that the worker reads from the database.
        :returns: The entry's key, or None if it could not be queued.
        """
        user_id = journal_user_id(request)
        is_authenticated = user_id is not None
        request_data = self.serialized_request(request, is_authenticated)
        response_data: JsonValue = None
        # pylint: disable=broad-exception-caught
        try:
            response_data = json.to_jsonable(data)
            record = SAMJournalEntryRecord(
                key=hash_factory(length=64),
                created_at=timezone.now(),
                user_id=user_id,
                thing=journal_field(thing),
                command=journal_field(command),
                status_code=status,
                request=json.to_jsonable(request_data),
                response=response_data,
            )
            queue_journal_entry(record, journal_sources)
        except Exception as e:
            # logged by smarter.lib.journal.receivers.journal_entry_failed_receiver().
            journal_entry_failed.send(
                sender=self.__class__,
                user=user_id,
                thing=str(thing),
                command=str(command),
                status=status,
                request=request,
                response=response_data,
                error=e,
            )
            return None
        return record.key

    def serialized_request(self, request: HttpRequest, is_authenticated: bool) -> SmarterDictType:
        """
        Return the request, serialized for the journal.

        :param request: The request.
        :param is_authenticated: Whether the request's user is authenticated, whose username is then
            serialized too.
        :returns: The serialized request, or an empty dict if it could not be serialized, e.g. an
            ``ASGIRequest`` without ``GET``.
        """
        prefix = f"{logger_prefix}.{self.formatted_class_name}.serialized_request()"
        serializer_class: type[HttpAnonymousRequestSerializer] = HttpAnonymousRequestSerializer
        if is_authenticated:
            serializer_class = HttpAuthenticatedRequestSerializer
        try:
            serialized: SmarterDictType = serializer_class(request).data
        except AttributeError:
            url = self.smarter_build_absolute_uri(request) or "Unknown URL"
            logger.error("%s %s could not serialize the request for %s", prefix, serializer_class.__name__, url)
            return {}
        return serialized


class SmarterJournaledJsonErrorResponse(SmarterJournaledJsonResponse):
    """
    Enhanced HTTP error response for Smarter CLI commands.

    This class serializes error information in a structured JSON format
    consumable by the Smarter CLI, allowing for consistent error formatting
    and display in the user console. It is the common error response for all
    CLI commands.

    A server error (5xx) is logged at ERROR, with its stack trace. A client error
    (4xx), e.g. an invalid api key or a rejected manifest, is expected, so it is
    logged at WARNING, without the stack trace.

    :param request: The original Django request object.
    :param e: The Python exception object that was raised.
    :param encoder: JSON encoder class. Defaults to :class:`smarter.lib.json.SmarterJSONEncoder`.
    :param safe: Controls if only ``dict`` objects may be serialized. Defaults to ``True``.
    :param thing: The resource or entity being operated on (noun).
    :param command: The CLI command executed on the resource.
    :param json_dumps_params: Additional kwargs for ``json.dumps()``.
    :param stack_trace: The stack trace for the exception.
    :param description: Human-readable error description. Defaults to the exception's ``message``
        attribute, if it has one.
    :param status: The HTTP status code. Defaults to 500.
    :param include_stack_trace: Whether the response includes ``stack_trace``. Defaults to ``True``.
        Responses that a browser may receive, e.g. those of the Smarter Chat apis, pass ``False``:
        the stack trace of a server error is still logged, but is never sent to the client.
    :param kwargs: Additional keyword arguments passed to the parent class.

    **Example error response JSON**, a :class:`~smarter.lib.journal.contract.models.SAMJournalApiErrorResponse`
    beside the envelope::

        {
            "error": {
                "errorClass": "SAMBrokerErrorNotFound",
                "stacktrace": "...",
                "description": "Guardrail example not found",
                "status": 404,
                "args": "url=https://...",
                "cause": "Python Exception",
                "context": "thing=Guardrail, command=describe",
                "thing": "Guardrail",
                "command": "describe"
            },
            "api": "smarter.sh/v1",
            "metadata": {"command": "describe", "thing": "Guardrail", "key": "4f1c...e9a2"}
        }
    """

    # the arguments of SmarterJournaledJsonResponse, and the error's.
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    def __init__(
        self,
        request: HttpRequest,
        e: Optional[Exception],
        encoder: type[JSONEncoder] = SmarterJSONEncoder,
        safe: bool = True,
        thing: Optional[Union[SmarterJournalThings, str]] = None,
        command: Optional[SmarterJournalCliCommands] = None,
        json_dumps_params: Optional[SmarterDictType] = None,
        stack_trace: str = "No stack trace available.",
        description: Optional[str] = None,
        status: int = HTTPStatus.INTERNAL_SERVER_ERROR.value,
        include_stack_trace: bool = True,
        **kwargs,
    ):
        error_class = "Unknown Exception"
        if e is not None:
            error_class = e.__class__.__name__
        if description is None:
            # SmarterException and its subclasses have a message.
            description = getattr(e, "message", None)

        url = self.smarter_build_absolute_uri(request) or "Unknown URL"
        if not status:
            status = HTTPStatus.INTERNAL_SERVER_ERROR.value
        args = "url=" + url
        cause = "Python Exception"
        if e is not None and e.__cause__ is not None:
            cause = f"{type(e.__cause__).__name__}: {e.__cause__}"
        context = "thing=" + str(thing) + ", command=" + str(command)
        error_description = None
        if description is not None:
            error_description = str(description)
        error_response = SAMJournalApiErrorResponse(
            error=SAMJournalApiErrorBody(
                errorClass=error_class,
                stacktrace=stack_trace,
                description=error_description,
                status=status,
                args=json.to_jsonable(args),
                cause=cause,
                context=context,
                thing=str(thing),
                command=str(command),
            )
        )
        init_prefix = f"{logger_prefix}.{self.formatted_class_name}.__init__()"
        if int(status) >= HTTPStatus.INTERNAL_SERVER_ERROR:
            # the server failed: log it with its stack trace, which, when include_stack_trace is
            # False, is never sent to the client.
            logger.error("%s %s", init_prefix, SmarterFormattedText.json(error_response.dump()))
        else:
            # the client's request was rejected, e.g. an invalid api key (401) or manifest (400):
            # expected, so a warning, and its stack trace is noise.
            logger.warning(
                "%s %s", init_prefix, SmarterFormattedText.json(error_response.dump(include_stack_trace=False))
            )
        data = error_response.dump(include_stack_trace=include_stack_trace)

        super().__init__(
            request=request,
            thing=thing,
            command=command,
            data=data,
            encoder=encoder,
            safe=safe,
            json_dumps_params=json_dumps_params,
            status=status,
            **kwargs,
        )
