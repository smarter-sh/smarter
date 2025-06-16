"""A Plugin that uses a REST API to retrieve its return data"""

# python stuff
import json
import logging
from typing import Any, Optional, Type

# smarter stuff
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import SettingsDefaults
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.utils import camel_to_snake
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys
from smarter.lib.openai.enum import OpenAIToolCallType

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
    _plugin_data: Optional[PluginDataApi] = None
    _plugin_data_serializer: Optional[PluginApiSerializer] = None

    @property
    def manifest(self) -> Optional[SAMApiPlugin]:
        """Return the Pydandic model of the plugin."""
        if not self._manifest and self.ready:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = SAMApiPlugin(**self.to_json())  # type: ignore[call-arg]
        return self._manifest if isinstance(self._manifest, SAMApiPlugin) else None

    @property
    def plugin_data(self) -> Optional[PluginDataApi]:
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
            self._plugin_data = PluginDataApi(**self.plugin_data_django_model)  # type: ignore[call-arg]
        if self.plugin_meta:
            # we don't have a Pydantic model but we do have an existing
            # Django ORM model instance, so we can use that directly.
            self._plugin_data = PluginDataApi.objects.get(
                plugin=self.plugin_meta,
            )
        # new Plugin scenario. there's nothing in the database yet.
        return self._plugin_data if isinstance(self._plugin_data, PluginDataApi) else None

    @property
    def plugin_data_class(self) -> Type[PluginDataApi]:
        """Return the plugin data class."""
        return PluginDataApi

    @property
    def plugin_data_serializer(self) -> Optional[PluginApiSerializer]:
        """Return the plugin data serializer."""
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginApiSerializer(self.plugin_data)
        return self._plugin_data_serializer if isinstance(self._plugin_data_serializer, PluginApiSerializer) else None

    @property
    def plugin_data_serializer_class(self) -> Type[PluginApiSerializer]:
        """Return the plugin data serializer class."""
        return PluginApiSerializer

    @property
    def plugin_data_django_model(self) -> Optional[dict[str, Any]]:
        """Return the plugin data definition as a json object."""
        if self._manifest:
            # recast the Pydantic model to the PluginDataApi Django ORM model
            api_connection = ApiConnection.objects.get(
                account=self.user_profile.account if self.user_profile else None,
                name=self.manifest.spec.connection if self.manifest else None,
            )
            api_data = self.manifest.spec.apiData.model_dump() if self.manifest and self.manifest.spec.apiData else None
            if not api_data:
                raise SmarterConfigurationError(
                    f"{self.name} PluginDataApi plugin_data_django_model() error: missing required apiData in manifest spec."
                )
            api_data = {camel_to_snake(key): value for key, value in api_data.items()}
            api_data["connection"] = api_connection
            return {
                "plugin": self.plugin_meta,
                "description": self.plugin_meta.description if self.plugin_meta else None,
                **api_data,
            }

    @property
    def custom_tool(self) -> Optional[dict[str, Any]]:
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
        if self.plugin_data and isinstance(self.plugin_data.parameters, dict):
            for key in self.plugin_data.parameters.keys() if self.plugin_data.parameters else {}:
                properties[key] = property_factory(param=self.plugin_data.parameters[key])

        if self.ready:
            return {
                OpenAIToolCallType.TYPE.value: OpenAIToolCallType.FUNCTION.value,
                OpenAIToolCallType.FUNCTION.value: {
                    OpenAIToolCallType.NAME.value: self.function_calling_identifier,
                    OpenAIToolCallType.DESCRIPTION.value: (
                        self.plugin_meta.description if self.plugin_meta else "No description provided."
                    ),
                    OpenAIToolCallType.PARAMETERS.value: {
                        OpenAIToolCallType.TYPE.value: OpenAIToolCallType.OBJECT.value,
                        OpenAIToolCallType.PROPERTIES.value: properties,
                        OpenAIToolCallType.REQUIRED.value: [],
                    },
                },
            }
        return None

    @classmethod
    def example_manifest(cls, kwargs: Optional[dict[str, Any]] = None) -> dict:

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
                            OpenAIToolCallType.NAME.value: "test",
                            OpenAIToolCallType.TYPE.value: "string",
                            OpenAIToolCallType.DESCRIPTION.value: "The test to run.",
                            OpenAIToolCallType.REQUIRED.value: True,
                            OpenAIToolCallType.DEFAULT.value: "test",
                        },
                        {
                            OpenAIToolCallType.NAME.value: "test2",
                            OpenAIToolCallType.TYPE.value: "string",
                            OpenAIToolCallType.DESCRIPTION.value: "The second test to run.",
                            OpenAIToolCallType.REQUIRED.value: False,
                            OpenAIToolCallType.DEFAULT.value: "test2",
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

    def tool_call_fetch_plugin_response(self, function_args: dict[str, Any]) -> Optional[str]:
        """
        Fetch information from a Plugin object.
        """
        raise NotImplementedError("tool_call_fetch_plugin_response() must be implemented in a subclass of PluginBase.")
