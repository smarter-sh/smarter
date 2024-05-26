# pylint: disable=W0613
"""Smarter API Manifest Abstract Broker class."""

import logging
import traceback

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest, JsonResponse

from smarter.common.api import SmarterApiVersions

from .enum import (
    SCLIResponseMetadata,
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
    """

    def __init__(
        self,
        request: HttpRequest,
        thing: SmarterJournalThings,
        command: SmarterJournalCliCommands,
        data,
        encoder=DjangoJSONEncoder,
        safe=True,
        json_dumps_params=None,
        **kwargs,
    ):
        data[SmarterJournalApiResponseKeys.API] = SmarterApiVersions.V1.value
        data[SmarterJournalApiResponseKeys.THING] = thing.value

        journal = SAMJournal.objects.create(
            user=request.user,
            thing=thing.value,
            command=command.value,
            request=request,
            response=data,
        )

        data[SmarterJournalApiResponseKeys.METADATA] = {
            SCLIResponseMetadata.KEY.value: journal.key,
        }

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

    def __init__(
        self,
        request: HttpRequest,
        thing: SmarterJournalThings,
        command: SmarterJournalCliCommands,
        e: Exception,
        encoder=DjangoJSONEncoder,
        safe=True,
        json_dumps_params=None,
        **kwargs,
    ):
        data = {
            "errorClass": e.__class__.__name__,
            "stacktrace": traceback.format_exc(),
            "description": e.args[0] if e.args else "",  # get the error message from args
            "status": e.status if hasattr(e, "status") else "",  # check if status attribute exists
            "args": e.args,
            "cause": str(e.__cause__),
            "context": str(e.__context__),
        }
        logger.error(data)

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
