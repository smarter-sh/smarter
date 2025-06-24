# pylint: disable=W0718
"""Smarter API SqlPlugin Manifest handler"""

import logging
from typing import Optional

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest

from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
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

    _plugin: Optional[PluginBase] = None
    _plugin_meta: Optional[PluginMeta] = None

    @property
    def plugin(self) -> Optional[PluginBase]:
        """
        PluginController() is a helper class to map the manifest model
        metadata.plugin_class to an instance of the the correct plugin class.
        """
        if self._plugin:
            return self._plugin
        if not self.user:
            raise SAMBrokerError(
                message="No user set for the broker",
                thing=self.thing,
                command=SmarterJournalCliCommands.CHAT,
            )
        if not self.account:
            raise SAMBrokerError(
                message="No account set for the broker",
                thing=self.thing,
                command=SmarterJournalCliCommands.CHAT,
            )
        controller = PluginController(
            request=self.smarter_request,
            user=self.user,
            account=self.account,
            manifest=self.manifest,  # type: ignore
            plugin_meta=self.plugin_meta if not self.manifest else None,
            name=self.name,
        )
        self._plugin = controller.obj
        return self._plugin

    @property
    def plugin_meta(self) -> Optional[PluginMeta]:
        if self._plugin_meta:
            return self._plugin_meta
        if self.name and self.account:
            try:
                self._plugin_meta = PluginMeta.objects.get(account=self.account, name=self.name)
            except PluginMeta.DoesNotExist:
                pass
        return self._plugin_meta

    def apply(self, request: WSGIRequest, *args, **kwargs) -> Optional[SmarterJournaledJsonResponse]:
        """
        apply the manifest. copy the manifest data to the Django ORM model and
        save the model to the database. Call super().apply() to ensure that the
        manifest is loaded and validated before applying the manifest to the
        Django ORM model.
        """
        super().apply(request, kwargs)
        logger.info("SAMPluginBaseBroker.apply() called %s with args: %s, kwargs: %s", request, args, kwargs)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        logger.info(
            "%s.describe() called %s with args: %s, kwargs: %s", self.formatted_class_name, request, args, kwargs
        )
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command, *args, **kwargs)

        if self.plugin and self.plugin.ready:
            try:
                data = self.plugin.to_json()
                if isinstance(data, dict):
                    data[SAMKeys.METADATA.value].get(SAMMetadataKeys.ACCOUNT.value)
                    data[SAMKeys.METADATA.value].get(SAMMetadataKeys.AUTHOR.value)
                # return self.json_response_ok(command=command, data=data) if isinstance(data, dict) else None
                return SmarterJournaledJsonResponse(
                    request=request,
                    command=command,
                    data=data,
                )
            except Exception as e:
                name = self.plugin_meta.name if self.plugin_meta else "unknown"
                raise SAMBrokerError(
                    f"{self.formatted_class_name} {name} describe failed",
                    thing=self.kind,
                    command=command,
                ) from e
        name = self.plugin_meta.name if self.plugin_meta else "unknown"
        raise SAMBrokerErrorNotReady(f"{self.formatted_class_name} {name} not ready", thing=self.kind, command=command)
