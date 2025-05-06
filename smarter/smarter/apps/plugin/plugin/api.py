"""A Plugin that uses a REST API to retrieve its return data"""

import logging
import re

from smarter.apps.plugin.manifest.enum import (
    SAMPluginMetadataClass,
    SAMPluginMetadataClassValues,
    SAMPluginMetadataKeys,
    SAMPluginSpecKeys,
    SAMPluginSpecPromptKeys,
    SAMPluginSpecSelectorKeys,
)
from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.apps.plugin.models import PluginDataApi, PluginDataApiConnection
from smarter.apps.plugin.serializers import PluginDataApiSerializer
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import SettingsDefaults
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

from .base import PluginBase


logger = logging.getLogger(__name__)


class PluginApi(PluginBase):
    """A Plugin that uses an http request to a REST API to retrieve its return data"""

    _metadata_class = SAMPluginMetadataClass.SQL_DATA.value
    _plugin_data: PluginDataApi = None
    _plugin_data_serializer: PluginDataApiSerializer = None

    @property
    def plugin_data(self) -> PluginDataApi:
        """Return the plugin data."""
        return self._plugin_data

    @property
    def plugin_data_class(self) -> type:
        """Return the plugin data class."""
        return PluginDataApi

    @property
    def plugin_data_serializer(self) -> PluginDataApiSerializer:
        """Return the plugin data serializer."""
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginDataApiSerializer(self.plugin_data)
        return self._plugin_data_serializer

    @property
    def plugin_data_serializer_class(self) -> PluginDataApiSerializer:
        """Return the plugin data serializer class."""
        return PluginDataApiSerializer

    @property
    def plugin_data_django_model(self) -> dict:
        """Return the plugin data definition as a json object."""

        def camel_to_snake(name):
            name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
            return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

        # recast the Pydantic model to the PluginDataApi Django ORM model
        plugin_data_apiconnection = PluginDataApiConnection.objects.get(
            account=self.user_profile.account, name=self.manifest.spec.data.sqlData.connection
        )
        api_data = self.manifest.spec.data.sqlData.model_dump()
        api_data = {camel_to_snake(key): value for key, value in api_data.items()}
        api_data["connection"] = plugin_data_apiconnection
        return {
            "plugin": self.plugin_meta,
            "description": self.manifest.spec.data.description,
            **api_data,
        }

    @property
    def custom_tool(self) -> dict:
        """Return the plugin tool. see https://platform.openai.com/docs/assistants/tools/function-calling/quickstart"""

        def property_factory(param) -> dict:
            try:
                param_type = param["type"]
                param_enum = param["enum"] if "enum" in param else None
                param_description = param["description"]
            except KeyError as e:
                raise SmarterConfigurationError(
                    f"{self.name} PluginApi custom_tool() error: missing required parameter key: {e}"
                ) from e

            if param_type not in PluginDataApi.DataTypes.all():
                raise SmarterConfigurationError(
                    f"{self.name} PluginApi custom_tool() error: invalid parameter type: {param_type}"
                )

            if param_enum and not isinstance(param_enum, list):
                raise SmarterConfigurationError(
                    f"{self.name} PluginApi custom_tool() error: invalid parameter enum: {param_enum}. Must be a list."
                )

            return {
                "type": param_type,
                "enum": param_enum,
                "description": param_description,
            }

        properties = {}
        for key in self.plugin_data.parameters.keys() if self.plugin_data.parameters else {}:
            properties[key] = property_factory(param=self.plugin_data.parameters[key])

        if self.ready:
            return {
                "type": "function",
                "function": {
                    "name": self.function_calling_identifier,
                    "description": self.plugin_data.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": [],
                    },
                },
            }
        return None

    @classmethod
    def example_manifest(cls, kwargs: dict = None) -> dict:
        return {
            SAMKeys.APIVERSION.value: SmarterApiVersions.V1,
            SAMKeys.KIND.value: MANIFEST_KIND,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.name: "ApiExample",
                SAMPluginMetadataKeys.PLUGIN_CLASS.value: SAMPluginMetadataClassValues.SQL.value,
                SAMMetadataKeys.DESCRIPTION.value: "Get additional information about the admin account of the Smarter platform.",
                SAMMetadataKeys.VERSION.value: "0.1.0",
                SAMMetadataKeys.TAGS.value: ["example.com", "api", "rest-api"],
            },
            SAMKeys.SPEC.value: {
                SAMPluginSpecKeys.SELECTOR.value: {
                    SAMPluginSpecSelectorKeys.DIRECTIVE.value: SAMPluginSpecSelectorKeys.SEARCHTERMS.value,
                    SAMPluginSpecSelectorKeys.SEARCHTERMS.value: ["admin", "Smarter platform", "admin account"],
                },
                SAMPluginSpecKeys.PROMPT.value: {
                    SAMPluginSpecPromptKeys.PROVIDER.value: SettingsDefaults.LLM_DEFAULT_PROVIDER,
                    SAMPluginSpecPromptKeys.SYSTEMROLE.value: "You are a helpful assistant for Smarter platform. You can provide information about the admin account of the Smarter platform.\n",
                    SAMPluginSpecPromptKeys.MODEL.value: SettingsDefaults.LLM_DEFAULT_MODEL,
                    SAMPluginSpecPromptKeys.TEMPERATURE.value: SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
                    SAMPluginSpecPromptKeys.MAXTOKENS.value: SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
                },
                SAMPluginSpecKeys.DATA.value: {
                    "description": "Query the Django User model to retrieve detailed account information about the admin account for the Smarter platform .",
                    SAMPluginMetadataClass.API_DATA.value: {
                        "connection": "exampleConnection",
                        "endpoint": "/api/v1/example-endpoint/",
                        "parameters": None,
                        "headers": None,
                        "body": "{'key1': 'value1', 'key2': 'value2'}",
                        "test_values": "",
                    },
                },
            },
        }

    def create(self):
        super().create()

        logger.info("PluginApi.create() called.")
