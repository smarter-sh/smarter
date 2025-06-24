# pylint: disable=W0718
"""Smarter Api ApiConnection Manifest handler"""

from logging import getLogger
from typing import Optional, Type

from django.core.handlers.wsgi import WSGIRequest

from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerErrorNotReady,
)


logger = getLogger(__name__)


class SAMConnectionBaseBroker(AbstractBroker):
    """
    Smarter API Connection Base Manifest Broker. This class is responsible for
    common tasks including portions of the apply()
    """

    _connection: Optional[TimestampedModel] = None

    @property
    def model_class(self) -> Type[TimestampedModel]:
        raise NotImplementedError(f"{self.formatted_class_name}.model_class must be implemented in the subclass.")

    @property
    def connection(self) -> Optional[TimestampedModel]:
        """Return the connection model instance."""
        raise NotImplementedError(f"{self.formatted_class_name}.connection must be implemented in the subclass.")

    def apply(self, request: WSGIRequest, *args, **kwargs) -> Optional[SmarterJournaledJsonResponse]:
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
        logger.info("SAMConnectionBaseBroker.apply() called %s with args: %s, kwargs: %s", request, args, kwargs)

        # update the common meta fields
        data = self.manifest.metadata.model_dump() if self.manifest else None
        data = self.camel_to_snake(data) if data else None
        if not isinstance(data, dict):
            raise SAMBrokerErrorNotReady(
                f"Manifest is not ready for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=SmarterJournalCliCommands.APPLY,
            )
        logger.info("SAMConnectionBaseBroker.apply() data: %s", data)

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
                logger.info("%s.apply() updating PluginMeta %s to %s", self.formatted_class_name, key, value)
                if getattr(self.connection, key) != value:
                    setattr(self.connection, key, value)
                    updated = True
        if updated:
            self.connection.save()
