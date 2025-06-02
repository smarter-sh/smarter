"""A Plugin that uses a REST API to retrieve its return data"""

# python stuff
import json
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
from ..manifest.models.api_plugin.const import MANIFEST_KIND
from ..manifest.models.api_plugin.enum import SAMApiPluginSpecApiData
from ..manifest.models.api_plugin.model import SAMApiPlugin
from ..models import ApiConnection, PluginDataApi
from ..serializers import PluginApiSerializer
from .base import PluginBase


logger = logging.getLogger(__name__)


class ApiPlugin(PluginBase):
    """A Plugin that uses an http request to a REST API to retrieve its return data"""

    _metadata_class = SAMPluginCommonMetadataClass.API.value
    _plugin_data: PluginDataApi = None
    _plugin_data_serializer: PluginApiSerializer = None

    @property
    def manifest(self) -> SAMApiPlugin:
        """Return the Pydandic model of the plugin."""
        if not self._manifest and self.ready:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = SAMApiPlugin(**self.to_json())
        return self._manifest

    @property
    def plugin_data(self) -> PluginDataApi:
        """
        Return the plugin data as a Django ORM instance.
        """
        if self._plugin_data:
            return self._plugin_data

        # we only want a preexisting manifest ostensibly sourced
        # from the cli, not a lazy-loaded
        if self._manifest and self.plugin_meta:
            # this is an update scenario. the Plugin exists in the database,
            # AND we've received manifest data from the cli.
            self._plugin_data = PluginDataApi(**self.plugin_data_django_model)
        if self.plugin_meta:
            # we don't have a Pydantic model but we do have an existing
            # Django ORM model instance, so we can use that directly.
            self._plugin_data = PluginDataApi.objects.get(
                plugin=self.plugin_meta,
            )
        # new Plugin scenario. there's nothing in the database yet.
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
        if self._manifest:
            # recast the Pydantic model to the PluginDataApi Django ORM model
            api_connection = ApiConnection.objects.get(
                account=self.user_profile.account, name=self.manifest.spec.connection
            )
            api_data = self.manifest.spec.apiData.model_dump()
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

        api_plugin = {
            SAMKeys.APIVERSION.value: SmarterApiVersions.V1,
            SAMKeys.KIND.value: MANIFEST_KIND,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "api_example",
                SAMPluginCommonMetadataKeys.PLUGIN_CLASS.value: SAMPluginCommonMetadataClassValues.API.value,
                SAMMetadataKeys.DESCRIPTION.value: "Get additional information about the admin account of the Smarter platform.",
                SAMMetadataKeys.VERSION.value: "0.1.0",
                SAMMetadataKeys.TAGS.value: ["example.com", "api", "rest-api"],
            },
            SAMKeys.SPEC.value: {
                SAMPluginSpecKeys.SELECTOR.value: {
                    SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value: SAMPluginCommonSpecSelectorKeys.SEARCHTERMS.value,
                    SAMPluginCommonSpecSelectorKeys.SEARCHTERMS.value: [
                        "admin",
                        "Smarter",
                        "account",
                    ],
                },
                SAMPluginSpecKeys.PROMPT.value: {
                    SAMPluginCommonSpecPromptKeys.PROVIDER.value: SettingsDefaults.LLM_DEFAULT_PROVIDER,
                    SAMPluginCommonSpecPromptKeys.SYSTEMROLE.value: "You are a helpful assistant for Smarter platform. You can provide information about the admin account of the Smarter platform.\n",
                    SAMPluginCommonSpecPromptKeys.MODEL.value: SettingsDefaults.LLM_DEFAULT_MODEL,
                    SAMPluginCommonSpecPromptKeys.TEMPERATURE.value: SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
                    SAMPluginCommonSpecPromptKeys.MAXTOKENS.value: SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
                },
                SAMPluginSpecKeys.CONNECTION.value: "example_connection",
                SAMPluginSpecKeys.API_DATA.value: {
                    "description": "Query the Django User model to retrieve detailed account information about the admin account for the Smarter platform .",
                    SAMApiPluginSpecApiData.ENDPOINT.value: "/api/v1/example-endpoint/",
                    SAMApiPluginSpecApiData.PARAMETERS.value: None,
                    SAMApiPluginSpecApiData.HEADERS.value: None,
                    SAMApiPluginSpecApiData.BODY.value: [
                        {
                            "name": "test",
                            "type": "string",
                            "description": "The test to run.",
                            "required": True,
                            "default": "test",
                        },
                        {
                            "name": "test2",
                            "type": "string",
                            "description": "The second test to run.",
                            "required": False,
                            "default": "test2",
                        },
                    ],
                    SAMApiPluginSpecApiData.TEST_VALUES.value: [
                        {"name": "username", "value": "admin"},
                        {"name": "limit", "value": 1},
                    ],
                    SAMApiPluginSpecApiData.LIMIT.value: 10,
                },
            },
        }
        # recast the Python dict to the Pydantic model
        # in order to validate our output
        pydantic_model = SAMApiPlugin(**api_plugin)
        return json.loads(pydantic_model.model_dump_json())

    def create(self):
        super().create()

        logger.info("PluginDataApi.create() called.")
