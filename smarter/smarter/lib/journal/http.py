# pylint: disable=W0613
"""
Journaled JSON responses of the Smarter api, and its common error response.

Every response of the cli api, and of other Smarter apis, is a :class:`SmarterJournaledJsonResponse`
or a :class:`SmarterJournaledJsonErrorResponse`. Each adds the api version and metadata envelope to
its data, and, while the ``ENABLE_JOURNAL`` switch is on, saves the request and response as a
:class:`~smarter.lib.journal.models.SAMJournal` entry.
"""

from http import HTTPStatus
from json import JSONEncoder
from typing import Any, Optional, Union

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, JsonResponse

from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.mixins import SmarterHelperMixin
from smarter.common.utils import is_authenticated_request
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
from .models import SAMJournal
from .signals import journal_entry_created, journal_entry_failed

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


class SmarterJournaledJsonResponse(JsonResponse, SmarterHelperMixin):
    """
    An enhanced HTTP response class for the Smarter API that augments standard Django JSON responses with additional manifest structure and metadata.

    This class is designed to provide a consistent response format for all Smarter API endpoints,
    embedding contextual information about the request and operation performed. It automatically
    attaches metadata such as the API version, the entity ("thing") being operated on, and the
    command executed. When journaling is enabled, it also creates a corresponding journal entry
    in the database, capturing the request, response, user, and status code for audit and traceability.

    Smarter-specific parameters include the original Django request object, the noun ("thing") being
    journaled, the command performed, and the API response data. Standard Django JsonResponse parameters
    such as ``data``, ``encoder``, ``safe``, and ``json_dumps_params`` are also supported.

    **Example:**

    A typical response data structure produced by this class::

        {
            "api": "v1",
            "thing": "account",
            "metadata": {
                "command": "create"
            }
        }

    When journaling is active, the metadata may also include a unique journal key for the entry.

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
    :param kwargs: Of these, only ``content_type``, ``status``, ``headers`` and ``reason`` are passed
        to :class:`django.http.JsonResponse`. The rest are ignored.
    """

    # pylint: disable=too-many-arguments
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
        **kwargs,
    ):
        if not isinstance(data, (dict, list)):
            # wrap any other data, e.g. a string, before adding the api version and metadata to it.
            data = {"response": data}
        envelope = SAMJournalApiEnvelope.build(command=command, thing=thing)
        if isinstance(data, dict):
            data.update(envelope.dump())

        init_prefix = f"{logger_prefix}.{self.formatted_class_name}.__init__()"

        def anonymous_serialized_request(request: HttpRequest) -> SmarterDictType:
            """Handles AttributeError: Got AttributeError when attempting to get a value for field `GET` on serializer `HttpAnonymousRequestSerializer`."""
            try:
                return HttpAnonymousRequestSerializer(request).data
            except AttributeError:
                url = self.smarter_build_absolute_uri(request) or "Unknown URL"
                logger.error(
                    "%s HttpAnonymousRequestSerializer could not serialize request data for %s",
                    init_prefix,
                    url,
                )
                return {}

        def authenticated_serialized_request(request: HttpRequest) -> SmarterDictType:
            """Handles the same but for authenticated requests."""
            try:
                return HttpAuthenticatedRequestSerializer(request).data
            except AttributeError:
                url = self.smarter_build_absolute_uri(request) or "Unknown URL"
                logger.error(
                    "%s HttpAuthenticatedRequestSerializer could not serialize request data for %s",
                    init_prefix,
                    url,
                )
                return {}

        if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_JOURNAL):
            # ASGIRequest can be finicky depending on the kind of response we're dealing with.
            # in general, we only want the user object if it's authenticated, which happens
            # when the user is logged in to the web console, and also when the request is made
            # via api, with a valid api key.
            #
            # Original exception text was:
            # 'ASGIRequest' object has no attribute 'user'.
            # AttributeError: 'PreparedRequest' object has no attribute 'user'
            try:
                if is_authenticated_request(request):
                    user = request.user
                    request_data = authenticated_serialized_request(request)
                else:
                    user = None
                    request_data = anonymous_serialized_request(request)
            except AttributeError:
                user = None
                request_data = anonymous_serialized_request(request)
            # pylint: disable=broad-except
            except Exception:
                logger.warning(
                    "%s Could not determine user from request, and, AttributeError was not raised.",
                    init_prefix,
                )
                user = None
                request_data = anonymous_serialized_request(request)

            serializable_data = None
            try:
                serializable_data = json.to_jsonable(data)
                # SAMJournal.user is a User, or None for an anonymous request.
                journal_user = None
                if user and not isinstance(user, AnonymousUser) and getattr(user, "is_authenticated", False):
                    journal_user = user
                # SAMJournal.thing and .command are blank, not NULL, when the response has none.
                # Django saves a value that isn't a str as str(value): so does this.
                journal_thing = ""
                if thing is not None:
                    journal_thing = str(thing)
                journal_command = ""
                if command is not None:
                    journal_command = str(command)
                journal = SAMJournal.objects.create(
                    user=journal_user,
                    thing=journal_thing,
                    command=journal_command,
                    request=request_data,
                    response=serializable_data,
                    status_code=status,
                )
                journal_entry_created.send(sender=self.__class__, journal=journal)
                if isinstance(data, dict):
                    # add the journal's key to the metadata, which keeps its command and thing.
                    envelope.metadata = SAMJournalApiMetadata(
                        command=envelope.metadata.command, thing=envelope.metadata.thing, key=journal.key
                    )
                    data.update(envelope.dump())
            # pylint: disable=broad-except
            except Exception as e:
                # logged by smarter.lib.journal.receivers.journal_entry_failed_receiver().
                journal_entry_failed.send(
                    sender=self.__class__,
                    user=user,
                    thing=str(thing),
                    command=str(command),
                    status=status,
                    request=request,
                    response=serializable_data,
                    error=e,
                )

        # Only pass allowed kwargs to JsonResponse
        allowed_kwargs = {}
        allowed_keys = {"content_type", "status", "headers", "reason"}
        for k in list(kwargs.keys()):
            if k in allowed_keys:
                allowed_kwargs[k] = kwargs.pop(k)
        super().__init__(
            data=data,
            encoder=encoder,
            safe=safe and isinstance(data, dict),
            json_dumps_params=json_dumps_params,
            status=status,
            **allowed_kwargs,
        )


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

    **Example error response JSON**::

        {
            "error": {
                "error_class": "ValueError",
                "stack_trace": "...",
                "description": "Invalid input",
                "status": 400,
                "args": "...",
                "cause": "...",
                "context": "thing=account, command=create"
            }
        }
    """

    # pylint: disable=too-many-arguments,too-many-locals
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
        if e:
            error_class = e.__class__.__name__
        if description is None:
            if isinstance(e, Exception) and hasattr(e, "message"):
                description = e.message  # type: ignore[union-attr]
            elif isinstance(e, str):
                description = e

        url = self.smarter_build_absolute_uri(request) or "Unknown URL"
        if not status:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        args = "url=" + url
        cause = "Python Exception"
        if isinstance(e, BaseException) and e.__cause__ is not None:
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
            description=description,
            safe=safe,
            json_dumps_params=json_dumps_params,
            status=status,
            **kwargs,
        )
