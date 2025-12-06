# pylint: disable=W0718
"""Smarter API SqlPlugin Manifest handler"""

import logging
from typing import Any, Optional

from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.plugin.spec import (
    SAMPluginCommonSpecPrompt,
    SAMPluginCommonSpecSelector,
)
from smarter.apps.plugin.manifest.models.enum import SAMPluginSpecCommonData
from smarter.apps.plugin.models import (
    PluginDataBase,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
)
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.common.conf import settings as smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import AbstractBroker, SAMBrokerError

from . import SAMPluginBrokerError


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        or waffle.switch_is_active(SmarterWaffleSwitches.MANIFEST_LOGGING)
    ) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


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
        Smarter API Plugin Manifest Broker.

        This abstract base class provides shared functionality for plugin brokers, including common logic for applying manifest data to Django ORM models. Subclasses must implement the `plugin_data` property to specify the concrete plugin data model.

        Responsibilities include:

        - Handling common tasks for plugin brokers, such as updating metadata and synchronizing manifest data.
        - Providing a standardized `apply()` method to copy manifest data to the database, with validation and logging.
        - Mapping manifest model metadata to the correct plugin class via `PluginController`.

        :param plugin: The plugin instance mapped from manifest metadata. May be set by subclasses or via `PluginController`.
        :type plugin: Optional[PluginBase]
        :param plugin_meta: The plugin metadata ORM instance. May be set by subclasses or resolved by name/account.
        :type plugin_meta: Optional[PluginMeta]
        :param plugin_data: The plugin data ORM instance. Must be implemented by subclasses.
        :type plugin_data: Optional[PluginDataBase]

        .. attention::

            The `PluginController` is used to map manifest metadata to the correct plugin class instance.

        .. error::
            Any error during manifest application, plugin resolution, or database update is logged and may raise an exception.

        .. seealso::

            :class:`AbstractBroker`
            :class:`PluginBase`
            :class:`PluginMeta`
            :class:`PluginDataBase`
            :class:`PluginController`

        **Example usage**::

            class MyPluginBroker(SAMPluginBaseBroker):
                @property
                def plugin_data(self):
                    return MyPluginData.objects.get(...)

            broker = MyPluginBroker(...)
            broker.apply(request, manifest_data=manifest_dict)
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
        """
        Retrieve the `PluginMeta` ORM instance associated with this broker.

        This property returns the plugin metadata object for the current plugin, resolving it by `name` and `account` if not already cached. If the metadata cannot be found, `None` is returned.

        :return: The `PluginMeta` instance for this broker, or `None` if unavailable.
        :rtype: Optional[PluginMeta]

        .. note::

            The metadata is cached after the first successful lookup for efficient repeated access.

        .. warning::

            If the plugin metadata does not exist in the database, no exception is raised; `None` is returned.

        .. seealso::

            :class:`PluginMeta`
            :meth:`SAMPluginBaseBroker.plugin`
            :meth:`SAMPluginBaseBroker.plugin_data`

        **Example usage**::

            meta = broker.plugin_meta
            if meta:
                print(meta.name, meta.account)
            else:
                print("No plugin metadata found.")

        """
        if self._plugin_meta:
            return self._plugin_meta
        if self.name and self.account:
            try:
                self._plugin_meta = PluginMeta.objects.get(account=self.account, name=self.name)
            except PluginMeta.DoesNotExist:
                pass
        return self._plugin_meta

    @property
    def plugin_data(self) -> Optional[PluginDataBase]:
        raise NotImplementedError("plugin_data property must be implemented in the subclass of SAMPluginBaseBroker")

    # --------------------------------------------------------------------------
    # ORM to Pydantic conversion methods
    # --------------------------------------------------------------------------

    def plugin_metadata_orm2pydantic(self) -> SAMPluginCommonMetadata:
        """
        Convert plugin metadata from the Django ORM model format to the Pydantic manifest format.

        This method transforms the plugin metadata, typically retrieved as a dictionary from the Django ORM (`PluginMeta`), into a Pydantic model (`SAMPluginCommonMetadata`). It ensures the metadata is properly camel-cased and validated for use in manifest serialization and API responses.

        :return: The plugin metadata as a Pydantic model.
        :rtype: SAMPluginCommonMetadata

        :raises SAMPluginBrokerError:
            If the plugin metadata or plugin instance is not found, or if conversion fails.

        .. error::

            Any error during conversion, such as missing metadata or invalid format, is wrapped and raised as :class:`SAMPluginBrokerError`.

        .. seealso::

            :class:`PluginMeta`
            :class:`SAMPluginCommonMetadata`
            :meth:`SAMPluginBaseBroker.plugin_meta`
            :meth:`SAMPluginBaseBroker.plugin`

        **Example usage**::

            metadata = broker.plugin_metadata_orm2pydantic()
            print(metadata.name, metadata.description)

        """
        command = SmarterJournalCliCommands("describe")
        if not self.plugin_meta:
            raise SAMPluginBrokerError(
                f"PluginMeta {self.name} not found",
                thing=self.kind,
                command=command,
            )
        if not self.plugin:
            raise SAMPluginBrokerError(
                f"Plugin {self.name} not found",
                thing=self.kind,
                command=command,
            )
        try:
            metadata = model_to_dict(self.plugin_meta)  # type: ignore[no-any-return]
            metadata = self.snake_to_camel(metadata)
            if not isinstance(metadata, dict):
                raise SAMPluginBrokerError(
                    f"Model dump failed for {self.kind} {self.plugin.name}",
                    thing=self.kind,
                    command=command,
                )
            logger.info(
                "%s.describe() PluginMeta %s %s",
                self.formatted_class_name,
                self.kind,
                metadata,
            )
            metadata = SAMPluginCommonMetadata(**metadata)
            return metadata
        except PluginMeta.DoesNotExist as e:
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} PluginMeta does not exist for {self.plugin.name}",
                thing=self.kind,
                command=command,
            ) from e
        except Exception as e:
            raise SAMPluginBrokerError(message=str(e), thing=self.kind, command=command) from e

    def plugin_data_orm2pydantic(self) -> dict[str, Any]:
        """
        Convert plugin data from the Django ORM model format to the Pydantic manifest format.

        This method transforms plugin data, typically retrieved as a dictionary from the Django ORM (`plugin_data`), into a format suitable for Pydantic manifest models. It handles conversion of nested structures, such as parameters, and ensures all fields are properly camel-cased and validated.

        :return: The plugin data as a dictionary formatted for Pydantic manifest models.
        :rtype: dict[str, Any]

        :raises SAMPluginBrokerError:
            If the plugin or plugin data is not found, or if conversion fails.

        .. note::

            - This method automatically converts parameter definitions from a dict-of-dicts to a list of dicts, merging required flags for each property.
            - The conversion process expects the plugin data to follow the expected ORM structure. Unexpected formats may result in errors.

        .. error::

            Any error during conversion, such as missing plugin data or invalid format, is wrapped and raised as :class:`SAMPluginBrokerError`.

        .. seealso::

            :class:`PluginDataBase`
            :meth:`SAMPluginBaseBroker.plugin_data`
            :meth:`SAMPluginBaseBroker.plugin`
            :class:`SAMPluginSpecCommonData`
            :class:`SmarterJournalCliCommands`


        **Example usage**::

            data = broker.plugin_data_orm2pydantic()
            print(data["parameters"])

        """
        command = SmarterJournalCliCommands("describe")
        if not self.plugin:
            raise SAMPluginBrokerError(
                f"Plugin {self.name} not found",
                thing=self.kind,
                command=command,
            )
        if not self.plugin_data:
            raise SAMPluginBrokerError(
                f"Plugin data not found for {self.kind} {self.plugin.name}",
                thing=self.kind,
                command=command,
            )
        plugin_data = model_to_dict(self.plugin_data)  # type: ignore[no-any-return]
        plugin_data = self.snake_to_camel(plugin_data)
        if not isinstance(plugin_data, dict):
            raise SAMPluginBrokerError(
                f"Model dump failed for {self.kind} {self.plugin.name}",
                thing=self.kind,
                command=command,
            )

        # pylint: disable=W0105
        """
        before transform, ['parameters']['properties'] is a dict of dicts
            {
                'id': 4171,
                'plugin': 4519,
                'description': 'This SQL query retrieves the Django user record for the username provided.\n',
                'parameters': {
                    'type': 'object',
                    'required': ['username'],
                    'properties': {
                        'unit': {'enum': ['Celsius', 'Fahrenheit'], 'type': 'string', 'description': 'The temperature unit to use.'},
                        'username': {'type': 'string', 'description': 'The username to query.'}
                        },
                    'additionalProperties': False
                },
                'plugindatabasePtr': 4171,
                'connection': 955,
                'sqlQuery': "SELECT * FROM auth_user WHERE username = '{username}';\n",
                'testValues': [{'name': 'username', 'value': 'admin'}, {'name': 'unit', 'value': 'Celsius'}],
                'limit': 10
            }

            after transform, ['parameters']['properties'] becomes a list of dicts where each dict has a 'name' key
            and the value is the original dict, e.g., and, the requirements list is re-merged into the properties dicts
            as the 'required' key (true, false) in each dict:

            {
            'id': 4171,
            'plugin': 4519,
            'description': 'This SQL query retrieves the Django user record for the username provided.\n',
            'parameters': [
                {
                    'name': 'unit',
                    'enum': ['Celsius', 'Fahrenheit'],
                    'type': 'string',
                    'required': false
                    'description': 'The temperature unit to use.'
                },
                {
                    'name': 'username',
                    'type': 'string',
                    'required': true
                    'description': 'The username to query.'
                }
            ],
            'plugindatabasePtr': 4171,
            'connection': 955,
            'sqlQuery': "SELECT * FROM auth_user WHERE username = '{username}';\n",
            'testValues': [{'name': 'username', 'value': 'admin'}, {'name': 'unit', 'value': 'Celsius'}],
            'limit': 10
            }
        """
        if SAMPluginSpecCommonData.PARAMETERS.value in plugin_data:
            parameters = plugin_data[SAMPluginSpecCommonData.PARAMETERS.value]
            if (
                isinstance(parameters, dict)
                and "properties" in parameters
                and isinstance(parameters["properties"], dict)
            ):
                properties_dict = parameters["properties"]
                required_list = parameters.get("required", [])
                # Convert dict of dicts to list of dicts with 'name' and 'required' keys
                properties_list = []
                for k, v in properties_dict.items():
                    prop = {"name": k, **v}
                    prop["required"] = k in required_list
                    properties_list.append(prop)
                plugin_data[SAMPluginSpecCommonData.PARAMETERS.value] = properties_list

        return plugin_data

    def plugin_prompt_orm2pydantic(self) -> SAMPluginCommonSpecPrompt:
        """
        Convert plugin prompt data from the Django ORM model format to the Pydantic manifest format.
        This method transforms the plugin prompt data, typically retrieved as a dictionary from the Django ORM (`PluginPrompt`), into a Pydantic model (`SAMPluginCommonSpecPrompt`). It ensures the prompt data is properly camel-cased and validated for use in manifest serialization and API responses.

        :return: The plugin prompt data as a Pydantic model.
        :rtype: SAMPluginCommonSpecPrompt
        :raises SAMPluginBrokerError:
            If the plugin prompt or plugin instance is not found, or if conversion fails.

        .. error::

            Any error during conversion, such as missing prompt data or invalid format, is wrapped and raised as :class:`SAMPluginBrokerError`.

        .. seealso::

            :class:`PluginPrompt`
            :class:`SAMPluginCommonSpecPrompt`
            :meth:`SAMPluginBaseBroker.plugin_prompt`
            :meth:`SAMPluginBaseBroker.plugin`

        **Example usage**::

            prompt = broker.plugin_prompt_orm2pydantic()
            print(prompt.template, prompt.variables)
        """
        command = SmarterJournalCliCommands("describe")
        if self.plugin_meta is None:
            raise SAMPluginBrokerError(
                f"PluginMeta {self.name} not found",
                thing=self.kind,
                command=command,
            )

        if self.plugin is None:
            raise SAMPluginBrokerError(
                f"Plugin {self.name} not found",
                thing=self.kind,
                command=command,
            )
        try:
            plugin_prompt = PluginPrompt.objects.get(plugin=self.plugin_meta)
            plugin_prompt = model_to_dict(plugin_prompt)  # type: ignore[no-any-return]
            plugin_prompt = self.snake_to_camel(plugin_prompt)
            if not isinstance(plugin_prompt, dict):
                raise SAMPluginBrokerError(
                    f"Model dump failed for {self.kind} {self.plugin.name}",
                    thing=self.kind,
                    command=command,
                )
            logger.info(
                "%s.describe() PluginPrompt %s %s",
                self.formatted_class_name,
                self.kind,
                plugin_prompt,
            )
            plugin_prompt = SAMPluginCommonSpecPrompt(**plugin_prompt)
            return plugin_prompt
        except PluginPrompt.DoesNotExist as e:
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} PluginPrompt does not exist for {self.plugin_meta.name}",
                thing=self.kind,
                command=command,
            ) from e
        except Exception as e:
            raise SAMPluginBrokerError(message=str(e), thing=self.kind, command=command) from e

    def plugin_selector_orm2pydantic(self) -> SAMPluginCommonSpecSelector:
        """
        Convert plugin selector data from the Django ORM model format to the Pydantic manifest format.

        This method transforms the plugin selector data, typically retrieved as a dictionary from the Django ORM (`PluginSelector`), into a Pydantic model (`SAMPluginCommonSpecSelector`). It ensures the selector data is properly camel-cased and validated for use in manifest serialization and API responses.

        :return: The plugin selector data as a Pydantic model.
        :rtype: SAMPluginCommonSpecSelector

        :raises SAMPluginBrokerError:
            If the plugin selector, plugin metadata, or plugin instance is not found, or if conversion fails.

        .. error::
            Any error during conversion, such as missing selector data or invalid format, is wrapped and raised as :class:`SAMPluginBrokerError`.

        .. seealso::

            :class:`PluginSelector`
            :class:`SAMPluginCommonSpecSelector`
            :meth:`SAMPluginBaseBroker.plugin`
            :meth:`SAMPluginBaseBroker.plugin_meta`

        **Example usage**::

            selector = broker.plugin_selector_orm2pydantic()
            print(selector.type, selector.options)

        """
        command = SmarterJournalCliCommands("describe")
        if self.plugin is None:
            raise SAMPluginBrokerError(
                f"Plugin {self.name} not found",
                thing=self.kind,
                command=command,
            )
        if self.plugin_meta is None:
            raise SAMPluginBrokerError(
                f"PluginMeta {self.name} not found",
                thing=self.kind,
                command=command,
            )
        try:
            plugin_selector = PluginSelector.objects.get(plugin=self.plugin_meta)
            plugin_selector = model_to_dict(plugin_selector)  # type: ignore[no-any-return]
            plugin_selector = self.snake_to_camel(plugin_selector)
            if not isinstance(plugin_selector, dict):
                raise SAMPluginBrokerError(
                    f"Model dump failed for {self.kind} {self.plugin.name}",
                    thing=self.kind,
                    command=command,
                )
            logger.info(
                "%s.describe() PluginSelector %s %s",
                self.formatted_class_name,
                self.kind,
                plugin_selector,
            )
            plugin_selector = SAMPluginCommonSpecSelector(**plugin_selector)
            return plugin_selector
        except PluginSelector.DoesNotExist as e:
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} PluginSelector does not exist for {self.plugin_meta.name}",
                thing=self.kind,
                command=command,
            ) from e
        except Exception as e:
            raise SAMPluginBrokerError(message=str(e), thing=self.kind, command=command) from e

    def apply(self, request: HttpRequest, *args, **kwargs) -> Optional[SmarterJournaledJsonResponse]:
        """
        Apply the manifest to the Django ORM model and persist changes to the database.

        This method orchestrates the application of manifest data by first invoking the superclass's `apply()` to ensure the manifest is loaded and validated. It then copies the manifest data to the corresponding Django ORM model and saves the model instance. Logging is performed to record the invocation and parameters.

        :param request: The HTTP request initiating the manifest application.
        :type request: HttpRequest
        :param args: Additional positional arguments passed to the method.
        :type args: tuple
        :param kwargs: Additional keyword arguments, typically including manifest data.
        :type kwargs: dict
        :return: Optionally returns a `SmarterJournaledJsonResponse` if the operation produces a journaled response, otherwise `None`.
        :rtype: Optional[SmarterJournaledJsonResponse]

        .. attention::

            - Always call `super().apply()` to guarantee manifest validation before applying changes to the ORM model.
            - Any error during manifest application, such as validation failure or database error, will be logged and may raise a `SAMPluginBrokerError`.


        .. seealso::

            :meth:`AbstractBroker.apply`
            :class:`SmarterJournaledJsonResponse`
            :class:`SAMPluginBrokerError`

        **Example usage**::

            response = broker.apply(request, manifest_data=manifest_dict)
            if response:
                print(response.status, response.data)
        """
        super().apply(request, kwargs)
        logger.info("SAMPluginBaseBroker.apply() called %s with args: %s, kwargs: %s", request, args, kwargs)
