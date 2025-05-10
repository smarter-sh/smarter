"""A Plugin that uses a REST API to retrieve its return data"""

# python stuff
import logging

# smarter stuff
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import SettingsDefaults
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.utils import camel_to_snake
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

# smarter plugin stuff
from ..manifest.enum import (
    SAMPluginCommonMetadataClass,
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonMetadataKeys,
    SAMPluginCommonSpecPromptKeys,
    SAMPluginCommonSpecSelectorKeys,
    SAMPluginSpecKeys,
)
from ..manifest.models.static_plugin.const import MANIFEST_KIND
from ..models import ApiConnection, PluginDataApi
from ..serializers import PluginApiSerializer
from .base import PluginBase


logger = logging.getLogger(__name__)


class ApiPlugin(PluginBase):
    """A Plugin that uses an http request to a REST API to retrieve its return data"""

    _metadata_class = SAMPluginCommonMetadataClass.SQL_DATA.value
    _plugin_data: PluginDataApi = None
    _plugin_data_serializer: PluginApiSerializer = None

    @property
    def plugin_data(self) -> PluginDataApi:
        """Return the plugin data."""
        return self._plugin_data

    @property
    def plugin_data_class(self) -> type:
        """Return the plugin data class."""
        return PluginDataApi

    @property
    def plugin_data_serializer(self) -> PluginApiSerializer:
        """Return the plugin data serializer."""
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginApiSerializer(self.plugin_data)
        return self._plugin_data_serializer

    @property
    def plugin_data_serializer_class(self) -> PluginApiSerializer:
        """Return the plugin data serializer class."""
        return PluginApiSerializer

    @property
    def plugin_data_django_model(self) -> dict:
        """Return the plugin data definition as a json object."""

        # recast the Pydantic model to the PluginDataApi Django ORM model
        api_connection = ApiConnection.objects.get(
            account=self.user_profile.account, name=self.manifest.spec.data.sqlData.connection
        )
        api_data = self.manifest.spec.data.sqlData.model_dump()
        api_data = {camel_to_snake(key): value for key, value in api_data.items()}
        api_data["connection"] = api_connection
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
                    f"{self.name} PluginDataApi custom_tool() error: missing required parameter key: {e}"
                ) from e

            if param_type not in PluginDataApi.DataTypes.all():
                raise SmarterConfigurationError(
                    f"{self.name} PluginDataApi custom_tool() error: invalid parameter type: {param_type}"
                )

            if param_enum and not isinstance(param_enum, list):
                raise SmarterConfigurationError(
                    f"{self.name} PluginDataApi custom_tool() error: invalid parameter enum: {param_enum}. Must be a list."
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
                SAMPluginCommonMetadataKeys.PLUGIN_CLASS.value: SAMPluginCommonMetadataClassValues.SQL.value,
                SAMMetadataKeys.DESCRIPTION.value: "Get additional information about the admin account of the Smarter platform.",
                SAMMetadataKeys.VERSION.value: "0.1.0",
                SAMMetadataKeys.TAGS.value: ["example.com", "api", "rest-api"],
            },
            SAMKeys.SPEC.value: {
                SAMPluginSpecKeys.SELECTOR.value: {
                    SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value: SAMPluginCommonSpecSelectorKeys.SEARCHTERMS.value,
                    SAMPluginCommonSpecSelectorKeys.SEARCHTERMS.value: ["admin", "Smarter platform", "admin account"],
                },
                SAMPluginSpecKeys.PROMPT.value: {
                    SAMPluginCommonSpecPromptKeys.PROVIDER.value: SettingsDefaults.LLM_DEFAULT_PROVIDER,
                    SAMPluginCommonSpecPromptKeys.SYSTEMROLE.value: "You are a helpful assistant for Smarter platform. You can provide information about the admin account of the Smarter platform.\n",
                    SAMPluginCommonSpecPromptKeys.MODEL.value: SettingsDefaults.LLM_DEFAULT_MODEL,
                    SAMPluginCommonSpecPromptKeys.TEMPERATURE.value: SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
                    SAMPluginCommonSpecPromptKeys.MAXTOKENS.value: SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
                },
                SAMPluginSpecKeys.DATA.value: {
                    "description": "Query the Django User model to retrieve detailed account information about the admin account for the Smarter platform .",
                    SAMPluginCommonMetadataClass.API_DATA.value: {
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

        logger.info("PluginDataApi.create() called.")
