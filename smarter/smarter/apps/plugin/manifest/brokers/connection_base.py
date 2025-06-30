# pylint: disable=W0718
"""Smarter Api ApiConnection Manifest handler"""

import logging
from typing import Optional, Type

from django.http import HttpRequest

from smarter.apps.plugin.models import ConnectionBase
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import AbstractBroker, SAMBrokerErrorNotReady


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.MANIFEST_LOGGING)
    ) and level <= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SAMConnectionBaseBroker(AbstractBroker):
    """
    Smarter API Connection Base Manifest Broker. This class is responsible for
    common tasks including portions of the apply()
    """

    _connection: Optional[ConnectionBase] = None

    @property
    def model_class(self) -> Type[ConnectionBase]:
        raise NotImplementedError(f"{self.formatted_class_name}.model_class must be implemented in the subclass.")

    @property
    def connection(self) -> Optional[ConnectionBase]:
        """Return the connection model instance."""
        raise NotImplementedError(f"{self.formatted_class_name}.connection must be implemented in the subclass.")

    def apply(self, request: HttpRequest, *args, **kwargs) -> Optional[SmarterJournaledJsonResponse]:
        """
        apply the manifest. copy the manifest data to the Django ORM model and
        save the model to the database. Call super().apply() to ensure that the
        manifest is loaded and validated before applying the manifest to the
        Django ORM model.
        Note that there are fields included in the manifest that are not editable
        and are therefore removed from the Django ORM model dict prior to attempting
        the save() command. These fields are defined in the readonly_fields list.
        """
        super().apply(request, kwargs)

        # update the common meta fields
        data = self.manifest.metadata.model_dump() if self.manifest else None
        data = self.camel_to_snake(data) if data else None
        if not isinstance(data, dict):
            raise SAMBrokerErrorNotReady(
                f"Manifest is not ready for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=SmarterJournalCliCommands.APPLY,
            )

        if self.connection is None:
            raise SAMBrokerErrorNotReady(
                f"Connection not found for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=SmarterJournalCliCommands.APPLY,
            )

        # Update metadata fields if they exist in data
        # {'name': 'test4818ca5097adb299', 'description': 'new description', 'version': '1.0.0', 'tags': None, 'annotations': None}
        updated = False
        for key, value in data.items():
            if hasattr(self.connection, key):
                if getattr(self.connection, key) != value:
                    setattr(self.connection, key, value)
                    logger.info("%s.apply() updating %s to %s", self.formatted_class_name, key, value)
                    updated = True
        if updated:
            self.connection.save()
