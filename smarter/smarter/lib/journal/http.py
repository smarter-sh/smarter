# pylint: disable=W0613
"""Smarter API Manifest Abstract Broker class."""

import logging
from http import HTTPStatus
from typing import Optional, Union

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest, JsonResponse

from smarter.common.api import SmarterApiVersions
from smarter.common.classes import SmarterHelperMixin
from smarter.common.utils import is_authenticated_request
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.http.serializers import (
    HttpAnonymousRequestSerializer,
    HttpAuthenticatedRequestSerializer,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseErrorKeys,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from .models import SAMJournal


logger = logging.getLogger(__name__)


class SmarterJournaledJsonResponse(JsonResponse, SmarterHelperMixin):
    """
    An enhanced HTTP response class that adds Smarter api manifest structural
    information and metadata.

    Smarter parameters:
    ---------------------------
    :request: The original Django request object.
    :thing: a noun. whatever it is that we're journaliing.
    :command: The command that was run on the thing.
    :data: The Smarter api response data for the request.

    Django inherited parameters:
    ---------------------------
    :param data: Data to be dumped into json. By default only ``dict`` objects
      are allowed to be passed due to a security flaw before ECMAScript 5. See
      the ``safe`` parameter for more information.
    :param encoder: Should be a json encoder class. Defaults to
      ``django.core.serializers.json.DjangoJSONEncoder``.
    :param safe: Controls if only ``dict`` objects may be serialized. Defaults
      to ``True``.
    :param json_dumps_params: A dictionary of kwargs passed to json.dumps().

    data = {
        "api": "v1",
        "thing": "account",
        "metadata": {
            "command": "create"
        },

    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request: HttpRequest,
        data,
        encoder=DjangoJSONEncoder,
        safe=True,
        thing: Optional[Union[SmarterJournalThings, str]] = None,
        command: Optional[SmarterJournalCliCommands] = None,
        json_dumps_params=None,
        **kwargs,
    ):
        status = kwargs.get("status", HTTPStatus.OK.value)
        data[SmarterJournalApiResponseKeys.API] = SmarterApiVersions.V1
        data[SmarterJournalApiResponseKeys.THING] = str(thing)
        data[SmarterJournalApiResponseKeys.METADATA] = {
            SCLIResponseMetadata.COMMAND: str(command),
        }

        def anonymous_serialized_request(request) -> dict:
            """
            handles AttributeError: Got AttributeError when attempting to get a value for field `GET` on serializer `HttpAnonymousRequestSerializer`.
            """
            try:
                return HttpAnonymousRequestSerializer(request).data
            except AttributeError:
                url = self.smarter_build_absolute_uri(request) or "Unknown URL"
                logger.error(
                    "SmarterJournaledJsonResponse() HttpAnonymousRequestSerializer could not serialize request data for %s",
                    url,
                )
                return {}

        def authenticated_serialized_request(request) -> dict:
            """
            handles the same but for authenticated requests
            """
            try:
                return HttpAuthenticatedRequestSerializer(request).data
            except AttributeError:
                url = self.smarter_build_absolute_uri(request) or "Unknown URL"
                logger.error(
                    "SmarterJournaledJsonResponse() HttpAuthenticatedRequestSerializer could not serialize request data for %s",
                    url,
                )
                return {}

        if waffle.switch_is_active(SmarterWaffleSwitches.JOURNAL):
            # WSGIRequest can be finicky depending on the kind of response we're dealing with.
            # in general, we only want the user object if it's authenticated, which happens
            # when the user is logged in to the web console, and also when the request is made
            # via api, with a valid api key.
            #
            # Original exception text was:
            # 'WSGIRequest' object has no attribute 'user'.
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
                logger.warning("Could not determine user from request, and, AttributeError was not raised.")
                user = None
                request_data = anonymous_serialized_request(request)

            try:
                serializable_data = json.loads(json.dumps(data, cls=DjangoJSONEncoder))
                journal = SAMJournal.objects.create(
                    user=user,
                    thing=thing,
                    command=command,
                    request=request_data,
                    response=serializable_data,
                    status_code=status,
                )
                data[SmarterJournalApiResponseKeys.METADATA] = {
                    SCLIResponseMetadata.KEY: journal.key,
                }
            # pylint: disable=broad-except
            except Exception as e:
                logger.error(
                    "user=%s, thing=%s, command=%s, status_code=%s\nrequest=%s\nresponse: %s",
                    user,
                    thing,
                    command,
                    status,
                    request,
                    serializable_data,
                )
                logger.error("SmarterJournaledJsonResponse()__init__() could not create journal entry: %s", e)

        super().__init__(data=data, encoder=encoder, safe=safe, json_dumps_params=json_dumps_params, **kwargs)


class SmarterJournaledJsonErrorResponse(SmarterJournaledJsonResponse):
    """
    Enhanced HTTP error response for Smarter CLI commands.

    This class serializes error information in a structured JSON format
    consumable by the Smarter CLI, allowing for consistent error formatting
    and display in the user console. It is the common error response for all
    CLI commands.

    :param request: The original Django request object.
    :type request: django.http.HttpRequest
    :param e: The Python exception object that was raised.
    :type e: Exception
    :param encoder: JSON encoder class. Defaults to ``django.core.serializers.json.DjangoJSONEncoder``.
    :type encoder: type
    :param safe: Controls if only ``dict`` objects may be serialized. Defaults to ``True``.
    :type safe: bool
    :param thing: The resource or entity being operated on (noun).
    :type thing: SmarterJournalThings or str, optional
    :param command: The CLI command executed on the resource.
    :type command: SmarterJournalCliCommands, optional
    :param json_dumps_params: Additional kwargs for ``json.dumps()``.
    :type json_dumps_params: dict, optional
    :param stack_trace: The stack trace for the exception.
    :type stack_trace: str, optional
    :param description: Human-readable error description.
    :type description: str, optional
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
        e: Exception,
        encoder=DjangoJSONEncoder,
        safe: bool = True,
        thing: Optional[Union[SmarterJournalThings, str]] = None,
        command: Optional[SmarterJournalCliCommands] = None,
        json_dumps_params: Optional[str] = None,
        stack_trace: str = "No stack trace available.",
        description: Optional[str] = None,
        **kwargs,
    ):
        status = kwargs.get("status", None)
        error_class = e.__class__.__name__ if e else "Unknown Exception"
        if description is None:
            if isinstance(e, Exception) and hasattr(e, "message"):
                description = e.message  # type: ignore[union-attr]
            elif isinstance(e, dict) and hasattr(e, "args"):
                description = e.args[0]
            elif isinstance(e, str):
                description = e

        url = self.smarter_build_absolute_uri(request) or "Unknown URL"
        status = str(status) if status else e.status if hasattr(e, "status") else 500  # type: ignore[union-attr]
        args = e.args if isinstance(e, dict) and hasattr(e, "args") else "url=" + url
        cause = str(e.__cause__) if isinstance(e, dict) and hasattr(e, "__cause__") else "Python Exception"
        context = (
            str(e.__context__)
            if isinstance(e, dict) and hasattr(e, "__context__")
            else "thing=" + str(thing) + ", command=" + str(command)
        )
        data = {}
        data[SmarterJournalApiResponseKeys.ERROR] = {
            SmarterJournalApiResponseErrorKeys.ERROR_CLASS: error_class,
            SmarterJournalApiResponseErrorKeys.STACK_TRACE: stack_trace,
            SmarterJournalApiResponseErrorKeys.DESCRIPTION: description,
            SmarterJournalApiResponseErrorKeys.STATUS: status,
            SmarterJournalApiResponseErrorKeys.ARGS: args,
            SmarterJournalApiResponseErrorKeys.CAUSE: cause,
            SmarterJournalApiResponseErrorKeys.CONTEXT: context,
        }
        logger.error(data[SmarterJournalApiResponseKeys.ERROR])

        super().__init__(
            request=request,
            thing=thing,
            command=command,
            data=data,
            encoder=encoder,
            safe=safe,
            json_dumps_params=json_dumps_params,
            **kwargs,
        )
