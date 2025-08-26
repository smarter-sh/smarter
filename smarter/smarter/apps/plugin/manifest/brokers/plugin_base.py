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
    ) and level >= logging.INFO


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

    @property
    def plugin_data(self) -> Optional[PluginDataBase]:
        raise NotImplementedError("plugin_data property must be implemented in the subclass of SAMPluginBaseBroker")

    # --------------------------------------------------------------------------
    # ORM to Pydantic conversion methods
    # --------------------------------------------------------------------------

    def plugin_metadata_orm2pydantic(self) -> SAMPluginCommonMetadata:
        """
        Convert the plugin metadata from a dict repr of the Dajngo ORM model
        format (ie the OpenAI Api format) to the Pydantic manifest format.

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
        Convert the plugin data from a dict repr of the Dajngo ORM model
        format (ie the OpenAI Api format) to the Pydantic manifest format.

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
        apply the manifest. copy the manifest data to the Django ORM model and
        save the model to the database. Call super().apply() to ensure that the
        manifest is loaded and validated before applying the manifest to the
        Django ORM model.
        """
        super().apply(request, kwargs)
        logger.info("SAMPluginBaseBroker.apply() called %s with args: %s, kwargs: %s", request, args, kwargs)
