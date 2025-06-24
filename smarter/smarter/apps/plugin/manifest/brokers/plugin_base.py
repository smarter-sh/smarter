# pylint: disable=W0718
"""Smarter API SqlPlugin Manifest handler"""

import logging
from typing import Optional

from django.core.handlers.wsgi import WSGIRequest

from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)


logger = logging.getLogger(__name__)


class SAMPluginBaseBroker(AbstractBroker):
    """
    Smarter API Plugin Manifest Broker. This class is responsible for
    common tasks including portions of the apply().
    """

    def apply(self, request: WSGIRequest, *args, **kwargs) -> Optional[SmarterJournaledJsonResponse]:
        """
        apply the manifest. copy the manifest data to the Django ORM model and
        save the model to the database. Call super().apply() to ensure that the
        manifest is loaded and validated before applying the manifest to the
        Django ORM model.
        """
        super().apply(request, kwargs)
        logger.info("SAMPluginBaseBroker.apply() called %s with args: %s, kwargs: %s", request, args, kwargs)
