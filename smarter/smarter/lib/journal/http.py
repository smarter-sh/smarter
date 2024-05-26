# pylint: disable=W0613
"""Smarter API Manifest Abstract Broker class."""

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
