# pylint: disable=W0718
"""Smarter Api ApiConnection Manifest handler"""

import logging
from typing import Optional, Type

from django.http import HttpRequest

from smarter.apps.plugin.models import ConnectionBase
from smarter.common.conf import settings as smarter_settings
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
        or waffle.switch_is_active(SmarterWaffleSwitches.MANIFEST_LOGGING)
    ) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SAMConnectionBaseBroker(AbstractBroker):
    """
    Smarter API Connection Base Manifest Broker.

    This abstract base class provides common functionality for API connection brokers, including shared logic for applying manifest data to Django ORM models. Subclasses must implement the `model_class` and `connection` properties to specify the concrete connection model and instance.

    Responsibilities include:

      - Handling common tasks for connection brokers, such as updating metadata fields.
      - Providing a standardized `apply()` method to copy manifest data to the database, with validation and logging.
      - Managing read-only fields and ensuring only editable fields are persisted.

    :param model_class: The Django ORM model class for the connection. Must be implemented by subclasses.
    :type model_class: Type[ConnectionBase]
    :param connection: The connection model instance. Must be implemented by subclasses.
    :type connection: Optional[ConnectionBase]

    .. seealso::

        :class:`AbstractBroker`
        :class:`ConnectionBase`
        :meth:`SAMConnectionBaseBroker.apply`

    **Example usage**::

        class MyConnectionBroker(SAMConnectionBaseBroker):
            @property
            def model_class(self):
                return MyConnectionModel

            @property
            def connection(self):
                return MyConnectionModel.objects.get(...)

        broker = MyConnectionBroker(...)
        broker.apply(request, manifest_data=manifest_dict)

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
        Apply the manifest by copying its metadata to the Django ORM model and saving it to the database.

        This method ensures the manifest is loaded and validated (via `super().apply`) before updating the database. Only editable fields from the manifest metadata are updated; read-only fields are excluded. All changes are logged, and the connection is saved if any updates occur.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments containing manifest data.
        :type kwargs: dict
        :return: Optionally returns a journaled JSON response, depending on subclass implementation.
        :rtype: Optional[SmarterJournaledJsonResponse]

        :raises SAMBrokerErrorNotReady:
            If the manifest is not ready or the connection instance is missing.

        .. error::

            Any error during manifest application or database update is logged and may raise an exception.

        .. seealso::

            :class:`ConnectionBase`
            :class:`SAMBrokerErrorNotReady`
            :meth:`SAMConnectionBaseBroker.apply`

        **Example usage**::

            broker.apply(request, manifest_data=manifest_dict)

        """
        logger.info("%s.apply() called with request: %s", self.formatted_class_name, request.build_absolute_uri())
        super().apply(request, kwargs)

        # update the common meta fields
        data = self.manifest.metadata.model_dump() if self.manifest else None
        data = self.camel_to_snake(data) if data else None
        if not isinstance(data, dict):
            raise SAMBrokerErrorNotReady(
                f"Manifest is not ready for {self.kind} broker. Cannot apply. manifest: {self.manifest.model_dump() if self.manifest else None}",
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
