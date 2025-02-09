# pylint: disable=W0613
"""Smarter API Manifest Abstract Broker class."""

import logging
import traceback
from http import HTTPStatus

import waffle
from django.core.handlers.wsgi import WSGIRequest
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest, JsonResponse

from smarter.common.api import SmarterApiVersions
from smarter.common.const import SmarterWaffleSwitches
from smarter.lib.django.http.serializers import (
    HttpAnonymousRequestSerializer,
    HttpAuthenticatedRequestSerializer,
)

from .enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseErrorKeys,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from .models import SAMJournal


logger = logging.getLogger(__name__)


class SmarterJournaledJsonResponse(JsonResponse):
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
        thing: SmarterJournalThings = None,
        command: SmarterJournalCliCommands = None,
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
                url = request.build_absolute_uri() if isinstance(request, WSGIRequest) else "Unknown URL"
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
                url = request.build_absolute_uri() if isinstance(request, WSGIRequest) else "Unknown URL"
                logger.error(
                    "SmarterJournaledJsonResponse() HttpAuthenticatedRequestSerializer could not serialize request data for %s",
                    url,
                )
                return {}

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_JOURNAL):
            # WSGIRequest can be finicky depending on the kind of response we're dealing with.
            # in general, we only want the user object if it's authenticated, which happens
            # when the user is logged in to the web console, and also when the request is made
            # via api, with a valid api key.
            #
            # Original exception text was:
            # 'WSGIRequest' object has no attribute 'user'.
            # AttributeError: 'PreparedRequest' object has no attribute 'user'
            try:
                if hasattr(request, "user") and request.user.is_authenticated:
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
                journal = SAMJournal.objects.create(
                    user=user,
                    thing=thing,
                    command=command,
                    request=request_data,
                    response=data,
                    status_code=status,
                )
                data[SmarterJournalApiResponseKeys.METADATA] = {
                    SCLIResponseMetadata.KEY: journal.key,
                }
            # pylint: disable=broad-except
            except Exception as e:
                logger.error("Could not create journal entry: %s", e)

        super().__init__(data=data, encoder=encoder, safe=safe, json_dumps_params=json_dumps_params, **kwargs)


class SmarterJournaledJsonErrorResponse(SmarterJournaledJsonResponse):
    """
    An enhanced HTTP error response class that serializes error information
    in a format that the cli can consume, format and echo to the user console.

    Smarter parameters:
    ---------------------------
    :request: The original Django request object.
    :thing: a noun. whatever it is that we're journaliing.
    :command: The command that was run on the thing.
    :e: a Python exception object that was raised.

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
    """

    # pylint: disable=too-many-arguments,too-many-locals
    def __init__(
        self,
        request: HttpRequest,
        e: Exception,
        encoder=DjangoJSONEncoder,
        safe=True,
        thing: SmarterJournalThings = None,
        command: SmarterJournalCliCommands = None,
        json_dumps_params=None,
        **kwargs,
    ):
        status = kwargs.get("status", None)
        error_class = e.__class__.__name__ if e else "Unknown Exception"
        description: str = ""
        if isinstance(e, Exception) and hasattr(e, "message"):
            description = e.message
        elif isinstance(e, dict) and hasattr(e, "args"):
            description = e.args[0]
        elif isinstance(e, str):
            description = e

        url = request.build_absolute_uri() if request else "Unknown URL"
        status = str(status) if status else e.status if hasattr(e, "status") else "500"
        args = e.args if isinstance(e, dict) and hasattr(e, "args") else "url=" + url
        cause = str(e.__cause__) if isinstance(e, dict) and hasattr(e, "__cause__") else "Python Exception"
        context = (
            str(e.__context__)
            if isinstance(e, dict) and hasattr(e, "__context__")
            else "thing=" + str(thing) + ", command=" + str(command)
        )
        try:
            stack_trace = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        # pylint: disable=broad-except
        except Exception:
            stack_trace = "No stack trace available."
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
